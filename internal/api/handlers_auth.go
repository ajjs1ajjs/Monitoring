package api

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/ajjs1ajjs/Monitoring/internal/auth"
	"github.com/ajjs1ajjs/Monitoring/internal/storage"
)

type userView struct {
	ID                 int64  `json:"id"`
	Username           string `json:"username"`
	IsAdmin            int    `json:"is_admin"`
	MustChangePassword int    `json:"must_change_password"`
	CreatedAt          string `json:"created_at"`
	LastLogin          string `json:"last_login"`
}

func toUserView(u *storage.User) userView {
	return userView{u.ID, u.Username, u.IsAdmin, u.MustChangePassword, u.CreatedAt, u.LastLogin}
}

func (a *App) handleLogin(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	u, err := a.Store.GetUserByUsername(strings.TrimSpace(body.Username))
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	if u == nil || !auth.VerifyPassword(u.PasswordHash, body.Password) {
		writeErr(w, http.StatusUnauthorized, "Invalid credentials")
		return
	}
	_ = a.Store.UpdateUser(u.ID, map[string]any{"last_login": storage.Now()})
	token, err := a.Auth.GenerateToken(u.ID, u.Username, u.IsAdmin == 1, u.MustChangePassword == 1)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Token generation failed")
		return
	}
	// The SPA session lives in an HttpOnly cookie so a stored-XSS payload can't
	// read the token from localStorage. Programmatic clients keep using the
	// returned access_token.
	a.setAuthCookie(w, r, token)
	// A generated one-time admin password is deleted after the first successful
	// login instead of lingering on disk.
	a.deleteAdminPasswordFile()
	a.audit(r, "login", "User "+u.Username+" logged in")
	writeJSON(w, http.StatusOK, map[string]any{
		"access_token": token,
		"token_type":   "bearer",
		"user":         toUserView(u),
	})
}

const authCookieName = "pymon_token"

func (a *App) setAuthCookie(w http.ResponseWriter, r *http.Request, token string) {
	http.SetCookie(w, &http.Cookie{
		Name:     authCookieName,
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		Secure:   r.TLS != nil,
		SameSite: http.SameSiteStrictMode,
	})
}

func (a *App) clearAuthCookie(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{Name: authCookieName, Value: "", Path: "/", HttpOnly: true, MaxAge: -1})
}

func (a *App) deleteAdminPasswordFile() {
	dir := filepath.Dir(a.Store.DBPath)
	_ = os.Remove(filepath.Join(dir, "admin_password.txt"))
}

func (a *App) handleLogout(w http.ResponseWriter, r *http.Request) {
	a.clearAuthCookie(w)
	a.audit(r, "logout", "User logged out")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleMe(w http.ResponseWriter, r *http.Request) {
	p := a.principal(r)
	u, err := a.Store.GetUserByID(p.UserID)
	if err != nil || u == nil {
		writeErr(w, http.StatusUnauthorized, "User not found")
		return
	}
	writeJSON(w, http.StatusOK, toUserView(u))
}

func (a *App) handleChangePassword(w http.ResponseWriter, r *http.Request) {
	var body struct {
		CurrentPassword string `json:"current_password"`
		NewPassword     string `json:"new_password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	p := a.principal(r)
	u, err := a.Store.GetUserByID(p.UserID)
	if err != nil || u == nil {
		writeErr(w, http.StatusUnauthorized, "User not found")
		return
	}
	if !auth.VerifyPassword(u.PasswordHash, body.CurrentPassword) {
		writeErr(w, http.StatusBadRequest, "Current password is incorrect")
		return
	}
	if !auth.CheckPasswordPolicy(body.NewPassword) {
		writeErr(w, http.StatusBadRequest, "New password must be at least 12 chars with upper, lower and digit")
		return
	}
	hash, err := auth.HashPassword(body.NewPassword)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Hashing failed")
		return
	}
	if err := a.Store.UpdateUser(u.ID, map[string]any{"password_hash": hash, "must_change_password": 0}); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "password_changed", "Password changed for "+u.Username)
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleCreateAPIKey(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Name string `json:"name"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	p := a.principal(r)
	token := "pymon_" + auth.RandomToken(32)
	hash, err := auth.HashPassword(token)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Hashing failed")
		return
	}
	sha := auth.SHA256Hex(token)
	id, err := a.Store.CreateAPIKey(p.UserID, hash, sha, body.Name)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "api_key_created", "API key '"+body.Name+"' created")
	writeJSON(w, http.StatusOK, map[string]any{"api_key": token, "name": body.Name, "id": id})
}

func (a *App) handleListAPIKeys(w http.ResponseWriter, r *http.Request) {
	p := a.principal(r)
	keys, err := a.Store.ListAPIKeys(p.UserID)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	out := make([]map[string]any, 0, len(keys))
	for _, k := range keys {
		out = append(out, map[string]any{
			"id": k.ID, "name": k.Name, "created_at": k.CreatedAt, "last_used": k.LastUsed,
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"api_keys": out})
}

func (a *App) handleDeleteAPIKey(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "key_id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid key id")
		return
	}
	p := a.principal(r)
	keys, _ := a.Store.ListAPIKeys(p.UserID)
	for _, k := range keys {
		if k.ID == id {
			if err := a.Store.DeleteAPIKey(id); err != nil {
				writeErr(w, http.StatusInternalServerError, "Database error")
				return
			}
			a.audit(r, "api_key_deleted", "API key deleted")
			writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
			return
		}
	}
	writeErr(w, http.StatusNotFound, "API key not found")
}

func (a *App) handleListUsers(w http.ResponseWriter, r *http.Request) {
	users, err := a.Store.ListUsers()
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	out := make([]userView, 0, len(users))
	for _, u := range users {
		out = append(out, toUserView(&u))
	}
	writeJSON(w, http.StatusOK, map[string]any{"users": out})
}

func (a *App) handleCreateUser(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Username string `json:"username"`
		Password string `json:"password"`
		IsAdmin  bool   `json:"is_admin"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	username := strings.TrimSpace(body.Username)
	if username == "" {
		writeErr(w, http.StatusBadRequest, "Username is required")
		return
	}
	if !auth.CheckPasswordPolicy(body.Password) {
		writeErr(w, http.StatusBadRequest, "Password must be at least 12 chars with upper, lower and digit")
		return
	}
	hash, err := auth.HashPassword(body.Password)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Hashing failed")
		return
	}
	isAdmin := 0
	if body.IsAdmin {
		isAdmin = 1
	}
	id, err := a.Store.CreateUser(username, hash, isAdmin)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			writeErr(w, http.StatusBadRequest, "Username already exists")
			return
		}
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "user_created", "User "+username+" created")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "user_id": id})
}

func (a *App) handleUpdateUser(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "user_id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid user id")
		return
	}
	u, err := a.Store.GetUserByID(id)
	if err != nil || u == nil {
		writeErr(w, http.StatusNotFound, "User not found")
		return
	}
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	fields := map[string]any{}
	if pw, ok := body["password"].(string); ok && pw != "" {
		if !auth.CheckPasswordPolicy(pw) {
			writeErr(w, http.StatusBadRequest, "Password must be at least 12 chars with upper, lower and digit")
			return
		}
		hash, err := auth.HashPassword(pw)
		if err != nil {
			writeErr(w, http.StatusInternalServerError, "Hashing failed")
			return
		}
		fields["password_hash"] = hash
		fields["must_change_password"] = 1
	}
	if v, ok := body["is_admin"].(bool); ok {
		admin := 0
		if v {
			admin = 1
		}
		if admin == 0 && u.IsAdmin == 1 {
			n, _ := a.Store.CountAdmins()
			if n <= 1 {
				writeErr(w, http.StatusBadRequest, "Cannot demote the last admin")
				return
			}
		}
		fields["is_admin"] = admin
	}
	if v, ok := body["must_change_password"].(bool); ok {
		n := 0
		if v {
			n = 1
		}
		fields["must_change_password"] = n
	}
	if len(fields) == 0 {
		writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
		return
	}
	if err := a.Store.UpdateUser(id, fields); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "user_updated", "User "+u.Username+" updated")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (a *App) handleDeleteUser(w http.ResponseWriter, r *http.Request) {
	id, err := pathInt(r, "user_id")
	if err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid user id")
		return
	}
	u, err := a.Store.GetUserByID(id)
	if err != nil || u == nil {
		writeErr(w, http.StatusNotFound, "User not found")
		return
	}
	if u.IsAdmin == 1 {
		n, _ := a.Store.CountAdmins()
		if n <= 1 {
			writeErr(w, http.StatusBadRequest, "Cannot delete the last admin")
			return
		}
	}
	if err := a.Store.DeleteUser(id); err != nil {
		writeErr(w, http.StatusInternalServerError, "Database error")
		return
	}
	a.audit(r, "user_deleted", "User "+u.Username+" deleted")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}
