package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
)

type Claims struct {
	UserID             int64  `json:"user_id"`
	Username           string `json:"sub"`
	IsAdmin            bool   `json:"is_admin"`
	MustChangePassword bool   `json:"must_change_password"`
	jwt.RegisteredClaims
}

type Auth struct {
	Secret     []byte
	ExpireTime time.Duration
}

func New(secretFile string, expireHours int) (*Auth, error) {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		if secretFile == "" {
			secretFile = ".pymon_jwt_secret"
		}
		b, err := os.ReadFile(secretFile)
		if err != nil {
			generated := RandomToken(32)
			if err := os.MkdirAll(filepath.Dir(secretFile), 0o700); err != nil && filepath.Dir(secretFile) != "." {
			}
			if err := os.WriteFile(secretFile, []byte(generated), 0o600); err != nil {
				return nil, fmt.Errorf("generate jwt secret: %w", err)
			}
			b = []byte(generated)
		}
		secret = strings.TrimSpace(string(b))
	}
	if len(secret) < 32 {
		fmt.Fprintln(os.Stderr, "WARNING: JWT secret is weak; generate a long random value")
	}
	expire := time.Duration(expireHours) * time.Hour
	if expire <= 0 {
		expire = 24 * time.Hour
	}
	return &Auth{Secret: []byte(secret), ExpireTime: expire}, nil
}

func (a *Auth) GenerateToken(userID int64, username string, isAdmin, mustChange bool) (string, error) {
	now := time.Now()
	claims := Claims{
		UserID:             userID,
		Username:           username,
		IsAdmin:            isAdmin,
		MustChangePassword: mustChange,
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   username,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(a.ExpireTime)),
		},
	}
	return jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString(a.Secret)
}

func (a *Auth) ParseToken(tokenStr string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenStr, &Claims{}, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method")
		}
		return a.Secret, nil
	})
	if err != nil {
		return nil, err
	}
	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, fmt.Errorf("invalid token")
	}
	return claims, nil
}

func HashPassword(pw string) (string, error) {
	b, err := bcrypt.GenerateFromPassword([]byte(pw), bcrypt.DefaultCost)
	return string(b), err
}

func VerifyPassword(hash, pw string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(pw)) == nil
}

func CheckPasswordPolicy(pw string) bool {
	if len(pw) < 12 {
		return false
	}
	hasUpper, hasLower, hasDigit := false, false, false
	for _, c := range pw {
		switch {
		case c >= 'A' && c <= 'Z':
			hasUpper = true
		case c >= 'a' && c <= 'z':
			hasLower = true
		case c >= '0' && c <= '9':
			hasDigit = true
		}
	}
	return hasUpper && hasLower && hasDigit
}

func RandomToken(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}

func SHA256Hex(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}
