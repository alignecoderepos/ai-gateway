package mcp

// Client placeholder for external tool execution via MCP.
type Client struct{}

func New() *Client { return &Client{} }

func (c *Client) Execute(tool string, input any) (any, error) {
	// TODO: implement MCP protocol
	return nil, nil
}
