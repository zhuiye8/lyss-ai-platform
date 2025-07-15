package client

import (
	"bufio"
	"io"
)

// SSEScanner Server-Sent Events 扫描器
type SSEScanner struct {
	scanner *bufio.Scanner
}

// NewSSEScanner 创建SSE扫描器
func NewSSEScanner(r io.Reader) *SSEScanner {
	scanner := bufio.NewScanner(r)
	
	// 设置缓冲区大小以处理大响应
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 1024*1024)
	
	return &SSEScanner{
		scanner: scanner,
	}
}

// Scan 扫描下一行
func (s *SSEScanner) Scan() bool {
	return s.scanner.Scan()
}

// Text 获取当前行文本
func (s *SSEScanner) Text() string {
	return s.scanner.Text()
}

// Err 获取扫描错误
func (s *SSEScanner) Err() error {
	return s.scanner.Err()
}