import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.stream.Collectors;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

// Run: java Sign.java  (JDK 21, no dependencies)
public class Sign {

  static String encode(String text) {
    return URLEncoder.encode(text, StandardCharsets.UTF_8)
        .replace("+", "%20").replace("*", "%2A").replace("%7E", "~");
  }

  static String canonicalQuery(String rawQuery) {
    List<String[]> pairs = new ArrayList<>();
    for (String part : rawQuery.split("&")) {
      if (part.isEmpty()) continue;
      String[] kv = part.split("=", 2);
      String name = URLDecoder.decode(kv[0], StandardCharsets.UTF_8);
      String value = kv.length > 1 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "";
      pairs.add(new String[] {name, value});
    }
    pairs.sort((a, b) -> a[0].equals(b[0]) ? a[1].compareTo(b[1]) : a[0].compareTo(b[0]));
    return pairs.stream().map(p -> encode(p[0]) + "=" + encode(p[1]))
        .collect(Collectors.joining("&"));
  }

  static String sha256Hex(byte[] data) throws Exception {
    MessageDigest digest = MessageDigest.getInstance("SHA-256");
    return HexFormat.of().formatHex(digest.digest(data));
  }

  static String sign(byte[] secret, String canonical) throws Exception {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(secret, "HmacSHA256"));
    byte[] result = mac.doFinal(canonical.getBytes(StandardCharsets.UTF_8));
    return HexFormat.of().formatHex(result);
  }

  static boolean signaturesMatch(String expectedHex, String receivedHex) {
    // MessageDigest.isEqual is a constant-time comparison
    return MessageDigest.isEqual(expectedHex.getBytes(StandardCharsets.US_ASCII),
        receivedHex.getBytes(StandardCharsets.US_ASCII));
  }

  public static void main(String[] args) throws Exception {
    byte[] demoSecret = "demo-secret-key-2026-10".getBytes(StandardCharsets.UTF_8); // example value
    byte[] body = "{\"item\":\"keyboard\",\"quantity\":2}".getBytes(StandardCharsets.UTF_8);
    String canonical = String.join("\n",
        "POST", "localhost:9410", "/orders",
        canonicalQuery("note=gift+wrap&currency=USD"),
        "1791200000", "n-0001", sha256Hex(body));
    System.out.println(canonical);
    String signature = sign(demoSecret, canonical);
    System.out.println("signature: " + signature);
    System.out.println("match: " + signaturesMatch(signature, signature));
  }
}
