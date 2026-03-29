// config.go — agentlens config set / config show commands
package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage CLI configuration (endpoint, api-key)",
}

var configSetCmd = &cobra.Command{
	Use:   "set <key> <value>",
	Short: "Set a configuration value",
	Long: `Set a configuration key to a value.

Supported keys:
  endpoint   Base URL of the AgentLens server (e.g. http://localhost:8000)
  api-key    API key for authentication`,
	Args: cobra.ExactArgs(2),
	RunE: runConfigSet,
}

var configShowCmd = &cobra.Command{
	Use:   "show",
	Short: "Display current configuration",
	Args:  cobra.NoArgs,
	RunE:  runConfigShow,
}

func init() {
	configCmd.AddCommand(configSetCmd)
	configCmd.AddCommand(configShowCmd)
}

func runConfigSet(cmd *cobra.Command, args []string) error {
	key, value := args[0], args[1]

	cfg, err := loadConfig()
	if err != nil {
		return err
	}

	switch key {
	case "endpoint":
		cfg.Endpoint = value
	case "api-key":
		cfg.APIKey = value
	default:
		return fmt.Errorf("unknown config key %q — valid keys: endpoint, api-key", key)
	}

	if err := saveConfig(cfg); err != nil {
		return err
	}

	displayVal := value
	if key == "api-key" && len(value) > 8 {
		displayVal = value[:4] + "****" + value[len(value)-4:]
	} else if key == "api-key" {
		displayVal = "****"
	}
	fmt.Fprintf(os.Stdout, "Config updated: %s = %s\n", key, displayVal)
	return nil
}

func runConfigShow(cmd *cobra.Command, args []string) error {
	cfg, err := loadConfig()
	if err != nil {
		return err
	}

	// Mask the API key for display.
	maskedKey := "(not set)"
	if cfg.APIKey != "" {
		if len(cfg.APIKey) > 8 {
			maskedKey = cfg.APIKey[:4] + "****" + cfg.APIKey[len(cfg.APIKey)-4:]
		} else {
			maskedKey = "****"
		}
	}

	endpoint := cfg.Endpoint
	if endpoint == "" {
		endpoint = "(not set)"
	}

	fmt.Fprintf(os.Stdout, "endpoint : %s\n", endpoint)
	fmt.Fprintf(os.Stdout, "api-key  : %s\n", maskedKey)
	return nil
}
