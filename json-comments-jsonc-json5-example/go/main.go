// Shows the encoding/json error for a comment and a trailing comma.
package main

import (
	"encoding/json"
	"fmt"
	"os"
)

func main() {
	for _, name := range []string{"orders-service.jsonc", "trailing-comma.jsonc"} {
		data, err := os.ReadFile("../config/" + name)
		if err != nil {
			panic(err)
		}
		var settings map[string]any
		if err := json.Unmarshal(data, &settings); err != nil {
			fmt.Printf("%s: %v\n", name, err)
		}
	}
}
