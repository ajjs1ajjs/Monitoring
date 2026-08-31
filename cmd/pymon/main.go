package main

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/api"
	"github.com/ajjs1ajjs/Monitoring/internal/auth"
	"github.com/ajjs1ajjs/Monitoring/internal/config"
	"github.com/ajjs1ajjs/Monitoring/internal/monitor"
	"github.com/ajjs1ajjs/Monitoring/internal/notify"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

const Version = "3.0.7"

func main() {
	if len(os.Args) < 2 {
		printUsage()
		return
	}
	switch os.Args[1] {
	case "--version", "-v":
		fmt.Println(Version)
	case "server":
		runServer(os.Args[2:])
	case "reset-admin":
		runResetAdmin(os.Args[2:])
	case "has-admin":
		runHasAdmin(os.Args[2:])
	default:
		printUsage()
	}
}

func printUsage() {
	fmt.Println("PyMon NOC " + Version)
	fmt.Println("Usage:")
	fmt.Println("  pymon server [--host HOST] [--port PORT] [--config PATH]")
	fmt.Println("  pymon reset-admin [--config PATH] [--db PATH]")
	fmt.Println("  pymon has-admin [--config PATH] [--db PATH]")
	fmt.Println("  pymon --version")
}

// runHasAdmin prints "yes"/"no" depending on whether the configured admin user
// exists. Used by the installer to decide whether to set a fresh password.
func runHasAdmin(args []string) {
	cfgPath, dbPath := parseCommonFlags(args)
	cfg, err := config.Load(cfgPath)
	if err != nil {
		fmt.Println("no")
		return
	}
	if dbPath == "" {
		dbPath = resolveDBPath(cfg)
	}
	db, abs, err := storage.Open(dbPath)
	if err != nil {
		fmt.Println("no")
		return
	}
	defer db.Close()
	store := storage.NewStore(db, abs)
	username := cfg.Auth.AdminUsername
	if username == "" {
		username = "admin"
	}
	u, err := store.GetUserByUsername(username)
	if err == nil && u != nil {
		fmt.Println("yes")
		return
	}
	fmt.Println("no")
}

func parseServerFlags(args []string) (host string, port int, cfgPath, dbPath string) {
	fs := flag.NewFlagSet("server", flag.ContinueOnError)
	fs.StringVar(&host, "host", "", "")
	fs.IntVar(&port, "port", 0, "")
	fs.StringVar(&cfgPath, "config", "", "")
	fs.StringVar(&dbPath, "db", "", "")
	_ = fs.Parse(args)
	return
}

func parseCommonFlags(args []string) (cfgPath, dbPath string) {
	fs := flag.NewFlagSet("common", flag.ContinueOnError)
	fs.StringVar(&cfgPath, "config", "", "")
	fs.StringVar(&dbPath, "db", "", "")
	_ = fs.Parse(args)
	return
}

func runServer(args []string) {
	host, port, cfgPath, dbPath := parseServerFlags(args)

	cfg, err := config.Load(cfgPath)
	if err != nil {
		log.Fatalf("config: %v", err)
	}
	if host != "" {
		cfg.Server.Host = host
	}
	if port != 0 {
		cfg.Server.Port = port
	}
	if dbPath == "" {
		dbPath = resolveDBPath(cfg)
	}

	db, abs, err := storage.Open(dbPath)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	store := storage.NewStore(db, abs)
	store.SetMaxBackups(cfg.Backup.MaxBackups)

	// Keep the JWT secret next to the database. systemd services run with CWD="/"
	// which the pymon user cannot write to, so a relative ".pymon_jwt_secret"
	// would crash startup on install (Permission denied).
	jwtSecretFile := filepath.Join(filepath.Dir(abs), ".pymon_jwt_secret")
	authn, err := auth.New(jwtSecretFile, cfg.Auth.JWTExpireHours)
	if err != nil {
		log.Fatalf("auth init: %v", err)
	}
	// Encrypt notification secrets at rest with a key derived from the JWT
	// secret (stable across restarts).
	store.SetEncryptionKey(authn.Secret)

	ensureAdmin(store, cfg, filepath.Dir(abs))

	ws := api.NewWSManager()
	notifySvc := notify.New(store)
	mon := monitor.New(cfg, store, ws, notifySvc)

	app := &api.App{
		Cfg:       cfg,
		Store:     store,
		Auth:      authn,
		WS:        ws,
		Monitor:   mon,
		Notify:    notifySvc,
		Metrics:   &api.MetricRegistry{},
		StartTime: time.Now(),
		Version:   api.Version{Version: Version},
		LogPath:   defaultLogPath(),
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	mon.Run(ctx)

	bindHost := cfg.Server.Host
	var addr string
	if bindHost == "" || bindHost == "0.0.0.0" {
		// Bind all interfaces on both IPv4 and IPv6 so "localhost" works in
		// browsers that resolve it to ::1 (a 0.0.0.0-only bind gets ERR_CONNECTION_REFUSED).
		addr = fmt.Sprintf(":%d", cfg.Server.Port)
	} else {
		addr = fmt.Sprintf("%s:%d", bindHost, cfg.Server.Port)
	}
	srv := &http.Server{
		Addr:         addr,
		Handler:      app.Handler(),
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
		<-sig
		log.Println("shutting down...")
		cancel()
		ctx2, cancel2 := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel2()
		_ = srv.Shutdown(ctx2)
	}()

	log.Printf("PyMon NOC %s listening on http://%s", Version, addr)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server: %v", err)
	}
}

func runResetAdmin(args []string) {
	cfgPath, dbPath := parseCommonFlags(args)
	cfg, err := config.Load(cfgPath)
	if err != nil {
		log.Fatalf("config: %v", err)
	}
	if dbPath == "" {
		dbPath = resolveDBPath(cfg)
	}
	db, abs, err := storage.Open(dbPath)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	store := storage.NewStore(db, abs)
	resetAdmin(store, cfg)
}

func resolveDBPath(cfg *config.Config) string {
	if p := os.Getenv("DB_PATH"); p != "" {
		return p
	}
	if cfg.Storage.Path != "" {
		return cfg.Storage.Path
	}
	return "pymon.db"
}

func defaultLogPath() string {
	if p := os.Getenv("LOG_DIR"); p != "" {
		return p + "/pymon.log"
	}
	if p := os.Getenv("DATA_DIR"); p != "" {
		return p + "/pymon.log"
	}
	return "pymon.log"
}

func adminPassword(cfg *config.Config) (string, bool) {
	if pw := os.Getenv("PYMON_ADMIN_PASSWORD"); pw != "" {
		return pw, true
	}
	if cfg.Auth.AdminPassword != "" &&
		cfg.Auth.AdminPassword != "change-me-on-first-login" &&
		cfg.Auth.AdminPassword != "291263" {
		return cfg.Auth.AdminPassword, true
	}
	return "", false
}

func randomToken(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}

// ensureAdmin creates the default admin user on first run.
func ensureAdmin(store *storage.Store, cfg *config.Config, dbDir string) {
	username := cfg.Auth.AdminUsername
	if username == "" {
		username = "admin"
	}
	u, err := store.GetUserByUsername(username)
	if err == nil && u != nil {
		return
	}
	createAdmin(store, cfg, username, dbDir)
}

func createAdmin(store *storage.Store, cfg *config.Config, username, dbDir string) {
	pw, ok := adminPassword(cfg)
	generated := !ok
	if !ok {
		pw = randomToken(18)
	}
	hash, err := auth.HashPassword(pw)
	if err != nil {
		log.Fatalf("hash password: %v", err)
	}
	if _, err := store.CreateUser(username, hash, 1); err != nil {
		log.Fatalf("create admin: %v", err)
	}
	if generated {
		fmt.Printf("Admin user '%s' created.\n", username)
		fmt.Printf("Generated password: %s\n", pw)
		fmt.Println("Change it immediately after first login!")
		// Persist the one-time password so it survives environments without
		// journald/systemd logging access. chmod 0600; delete after login.
		if dbDir != "" {
			pwFile := filepath.Join(dbDir, "admin_password.txt")
			if err := os.WriteFile(pwFile, []byte(pw+"\n"), 0o600); err == nil {
				fmt.Printf("One-time password saved to %s (delete it after login).\n", pwFile)
			}
		}
	} else {
		fmt.Printf("Admin user '%s' created (password from config/env).\n", username)
	}
}

func resetAdmin(store *storage.Store, cfg *config.Config) {
	username := cfg.Auth.AdminUsername
	if username == "" {
		username = "admin"
	}
	if u, err := store.GetUserByUsername(username); err == nil && u != nil {
		_ = store.DeleteUser(u.ID)
	}
	createAdmin(store, cfg, username, filepath.Dir(store.DBPath))
}
