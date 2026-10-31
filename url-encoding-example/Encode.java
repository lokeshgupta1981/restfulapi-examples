import java.net.URI;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.List;

// How Java encodes the same values (JDK 25, no dependencies).
public class Encode {
    static final String BASE = "http://127.0.0.1:9160";

    // Prints a string in quotes, with non-ASCII characters as \\uXXXX.
    static String show(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            sb.append(c < 0x7f ? String.valueOf(c) : String.format("\\u%04x", (int) c));
        }
        return sb.append('"').toString();
    }

    // Joins the pretty-printed JSON response onto one line.
    static String compact(String json) {
        return json.replaceAll("\\n\\s*", "");
    }

    static String get(HttpClient client, URI uri) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(uri).build();
        return compact(client.send(request, HttpResponse.BodyHandlers.ofString()).body());
    }

    public static void main(String[] args) throws Exception {
        // "caf\u00e9" is "cafe" with an accented e (U+00E9).
        List<String> values = List.of("C++ & Java/Go", "caf\u00e9", "50% off", "~user*(1)!");

        System.out.println("URLEncoder.encode(v, UTF_8):");
        for (String v : values) {
            String encoded = URLEncoder.encode(v, StandardCharsets.UTF_8);
            System.out.printf("  %-18s -> %s%n", show(v), encoded);
        }

        HttpClient client = HttpClient.newHttpClient();

        System.out.println("new URI(scheme, authority, path, query, fragment):");
        URI uri = new URI("http", "127.0.0.1:9160", "/v2/docs/report", "tag=C++ & Java/Go", null);
        System.out.println("  " + uri.getRawPath() + "?" + uri.getRawQuery());
        System.out.println("  server got: " + get(client, uri));

        System.out.println("Encoded each value first:");
        String segment = URLEncoder.encode("AB/12 caf\u00e9", StandardCharsets.UTF_8)
                .replace("+", "%20");
        String tag = URLEncoder.encode("C++ & Java/Go", StandardCharsets.UTF_8);
        URI fixed = URI.create(BASE + "/v2/docs/" + segment + "?tag=" + tag);
        System.out.println("  " + fixed.getRawPath() + "?" + fixed.getRawQuery());
        System.out.println("  server got: " + get(client, fixed));

        System.out.println("URLDecoder.decode(\"a+b%2Bc\", UTF_8): "
                + URLDecoder.decode("a+b%2Bc", StandardCharsets.UTF_8));
    }
}
