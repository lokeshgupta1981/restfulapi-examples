// Which decoders accept which input? Run: java DecoderMatrix.java
import java.util.*;
public class DecoderMatrix{public static void main(String[] a){
 LinkedHashMap<String,String> c=new LinkedHashMap<>();c.put("std padded","PDw/Pz8+Pg==");c.put("std no pad","PDw/Pz8+Pg");c.put("url padded","PDw_Pz8-Pg==");c.put("url no pad","PDw_Pz8-Pg");c.put("bad char","PDw*Pz8+Pg==");
 Map<String,Base64.Decoder> d=new LinkedHashMap<>();d.put("getDecoder",Base64.getDecoder());d.put("getUrlDecoder",Base64.getUrlDecoder());d.put("getMimeDecoder",Base64.getMimeDecoder());
 for(var e:d.entrySet()){StringBuilder sb=new StringBuilder(e.getKey()+" |");for(var k:c.entrySet()){try{sb.append(" "+k.getKey()+"=ok("+new String(e.getValue().decode(k.getValue()))+")");}catch(Exception x){sb.append(" "+k.getKey()+"=ERR");}}System.out.println(sb);}
}}
