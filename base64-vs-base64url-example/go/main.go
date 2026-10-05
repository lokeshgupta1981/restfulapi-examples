// Base64 vs Base64URL in Go. Run: go run .
package main

import (
	"encoding/base64"
	"fmt"
)

func main() {
	data := []byte("<<???>>")

	fmt.Println("StdEncoding    :", base64.StdEncoding.EncodeToString(data))
	fmt.Println("URLEncoding    :", base64.URLEncoding.EncodeToString(data))
	fmt.Println("RawURLEncoding :", base64.RawURLEncoding.EncodeToString(data))

	decoded, err := base64.RawURLEncoding.DecodeString("PDw_Pz8-Pg")
	fmt.Printf("RawURLEncoding.DecodeString(\"PDw_Pz8-Pg\")   -> %q, err=%v\n", decoded, err)

	_, err = base64.URLEncoding.DecodeString("PDw_Pz8-Pg")
	fmt.Println("URLEncoding.DecodeString(\"PDw_Pz8-Pg\")      -> err =", err)

	_, err = base64.RawURLEncoding.DecodeString("PDw_Pz8-Pg==")
	fmt.Println("RawURLEncoding.DecodeString(\"PDw_Pz8-Pg==\") -> err =", err)

	_, err = base64.StdEncoding.DecodeString("PDw_Pz8-Pg==")
	fmt.Println("StdEncoding.DecodeString(\"PDw_Pz8-Pg==\")    -> err =", err)
}
