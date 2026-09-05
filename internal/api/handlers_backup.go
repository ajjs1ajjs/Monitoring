package api

import (
	"encoding/json"
	"net/http"
	"path/filepath"
)

func (a *App) handleBackupList(w http.ResponseWriter, r *http.Request) {
	dir := a.Cfg.Backup.BackupDir
	if dir == "" {
		dir = "backups"
	}
	backups, err := a.Store.ListBackups(dir)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Failed to list backups")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"backups": backups})
}

func (a *App) handleBackupCreate(w http.ResponseWriter, r *http.Request) {
	dir := a.Cfg.Backup.BackupDir
	if dir == "" {
		dir = "backups"
	}
	name, err := a.Store.BackupTo(dir)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "Backup failed: "+err.Error())
		return
	}
	a.audit(r, "backup_created", "Backup "+name+" created")
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "filename": name})
}

func (a *App) handleBackupRestore(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Filename string `json:"filename"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeErr(w, http.StatusBadRequest, "Invalid request body")
		return
	}
	if body.Filename == "" {
		writeErr(w, http.StatusBadRequest, "filename is required")
		return
	}
	dir := a.Cfg.Backup.BackupDir
	if dir == "" {
		dir = "backups"
	}
	if err := a.Store.RestoreFrom(dir, filepath.Base(body.Filename)); err != nil {
		writeErr(w, http.StatusBadRequest, "Restore failed: "+err.Error())
		return
	}
	a.audit(r, "backup_restored", "Restored from "+body.Filename)
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "restored_from": body.Filename})
}
