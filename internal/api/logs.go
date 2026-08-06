package api

import (
	"os"
)

func (a *App) LogFilePath() string {
	if a.LogPath != "" {
		return a.LogPath
	}
	return "pymon.log"
}

func tailLogFile(path string, lines int) string {
	f, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		return ""
	}
	const chunk = 8192
	start := st.Size()
	buf := make([]byte, 0, lines*200)
	read := int64(0)
	for start > 0 {
		size := chunk
		if start < int64(size) {
			size = int(start)
		}
		start -= int64(size)
		tmp := make([]byte, size)
		if _, err := f.ReadAt(tmp, start); err != nil {
			break
		}
		buf = append(append(make([]byte, 0, size+len(buf)), tmp...), buf...)
		read += int64(size)
		if linesCount(buf) >= lines && read >= int64(len(buf)) {
			break
		}
	}
	s := string(buf)
	// trim to last N lines
	for i := 0; i < len(s) && lines > 0; i++ {
		if s[i] == '\n' {
			lines--
			if lines == 0 {
				s = s[i+1:]
				break
			}
		}
	}
	return s
}

func linesCount(b []byte) int {
	n := 1
	for _, c := range b {
		if c == '\n' {
			n++
		}
	}
	return n
}

func truncateLogFile(path string) error {
	return os.Truncate(path, 0)
}
