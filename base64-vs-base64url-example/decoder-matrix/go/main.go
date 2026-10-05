// Which decoders accept which input? Run: go run .
package main
import ("encoding/base64";"fmt")
func main(){
 keys:=[]string{"std padded","std no pad","url padded","url no pad","bad char"}
 vals:=[]string{"PDw/Pz8+Pg==","PDw/Pz8+Pg","PDw_Pz8-Pg==","PDw_Pz8-Pg","PDw*Pz8+Pg=="}
 encs:=map[string]*base64.Encoding{"StdEncoding":base64.StdEncoding,"RawStdEncoding":base64.RawStdEncoding,"URLEncoding":base64.URLEncoding,"RawURLEncoding":base64.RawURLEncoding}
 for _,n:=range []string{"StdEncoding","RawStdEncoding","URLEncoding","RawURLEncoding"}{
  fmt.Print(n," |")
  for i,k:=range keys{ b,err:=encs[n].DecodeString(vals[i]); if err!=nil{fmt.Print(" ",k,"=ERR")}else{fmt.Printf(" %s=ok(%q)",k,b)}}
  fmt.Println()}
}
