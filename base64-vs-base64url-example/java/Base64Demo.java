import java.nio.charset.StandardCharsets;
import java.util.Base64;

// Base64 vs Base64URL in Java 8+. Run: java Base64Demo.java
public class Base64Demo {
    public static void main(String[] args) {
        byte[] data = "<<???>>".getBytes(StandardCharsets.UTF_8);

        String standard = Base64.getEncoder().encodeToString(data);
        String urlSafe = Base64.getUrlEncoder().encodeToString(data);
        String urlSafeNoPad = Base64.getUrlEncoder().withoutPadding().encodeToString(data);
        System.out.println("base64          : " + standard);
        System.out.println("base64url       : " + urlSafe);
        System.out.println("base64url no pad: " + urlSafeNoPad);

        // The decoders accept input with or without padding
        byte[] decoded = Base64.getUrlDecoder().decode("PDw_Pz8-Pg");
        System.out.println("url decoder, no padding: " + new String(decoded, StandardCharsets.UTF_8));

        // The basic decoder rejects the URL-safe characters
        try {
            Base64.getDecoder().decode("PDw_Pz8-Pg");
        } catch (IllegalArgumentException e) {
            System.out.println("basic decoder on url text: " + e.getMessage());
        }

        // The MIME encoder adds CRLF every 76 characters
        byte[] sixty = new byte[60];
        String mime = Base64.getMimeEncoder().encodeToString(sixty);
        System.out.println("MIME encoder, 60 bytes -> contains CRLF: " + mime.contains("\r\n"));
    }
}
