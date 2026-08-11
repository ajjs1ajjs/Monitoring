package storage

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"io"
	"strings"
)

const encPrefix = "enc:"

// SetEncryptionKey configures a key for encrypting sensitive values (e.g.
// notification secrets) at rest. The key is derived from the JWT secret so it
// is stable across restarts. When unset, values are stored as-is (used during
// initial provisioning and in tests).
func (st *Store) SetEncryptionKey(secret []byte) {
	sum := sha256.Sum256(secret)
	st.secretKey = sum[:]
}

// encryptText returns "enc:<base64(nonce+ciphertext)>" when a key is
// configured, otherwise the plaintext unchanged.
func (st *Store) encryptText(plain string) (string, error) {
	if len(st.secretKey) == 0 {
		return plain, nil
	}
	block, err := aes.NewCipher(st.secretKey)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}
	sealed := gcm.Seal(nonce, nonce, []byte(plain), nil)
	return encPrefix + base64.StdEncoding.EncodeToString(sealed), nil
}

// decryptText reverses encryptText; plaintext values (legacy rows) are
// returned unchanged.
func (st *Store) decryptText(enc string) (string, error) {
	if !strings.HasPrefix(enc, encPrefix) {
		return enc, nil
	}
	if len(st.secretKey) == 0 {
		return "", fmt.Errorf("encrypted value found but no encryption key configured")
	}
	raw, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(enc, encPrefix))
	if err != nil {
		return "", err
	}
	block, err := aes.NewCipher(st.secretKey)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	if len(raw) < gcm.NonceSize() {
		return "", fmt.Errorf("encrypted value too short")
	}
	nonce, ciphertext := raw[:gcm.NonceSize()], raw[gcm.NonceSize():]
	plain, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", fmt.Errorf("failed to decrypt stored value (key changed?)")
	}
	return string(plain), nil
}
