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
	"strings"
	"syscall"
	"time"

	"github.com/ajjs1ajjs/Monitoring/internal/api"
	"github.com/ajjs1ajjs/Monitoring/internal/auth"
	"github.com/ajjs1ajjs/Monitoring/internal/config"
	"github.com/ajjs1ajjs/Monitoring/internal/monitor"
	"github.com/ajjs1ajjs/Monitoring/internal/notify"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

const Version = "3.0.0"

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
	default:
		printUsage()
	}
}

func printUsage() {
	fmt.Println("PyMon NOC " + Version)
	fmt.Println("Usage:")
	fmt.Println("  pymon server [--host HOST] [--port PORT] [--config PATH]")
	fmt.Println("  pymon reset-admin [--config PATH] [--db PATH]")
	fmt.Println("  pymon --version")
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

	ensureAdmin(store, cfg)

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

	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
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
func ensureAdmin(store *storage.Store, cfg *config.Config) {
	username := cfg.Auth.AdminUsername
	if username == "" {
		username = "admin"
	}
	u, err := store.GetUserByUsername(username)
	if err == nil && u != nil {
		return
	}
	createAdmin(store, cfg, username)
}

func createAdmin(store *storage.Store, cfg *config.Config, username string) {
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
	createAdmin(store, cfg, username)
}

var _ = strings.TrimSpace
