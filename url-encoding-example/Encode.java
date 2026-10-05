import java.net.URI;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.List;

// How Java encodes the same values (JDK 21, no dependencies).
public class Encode {
    static final String BASE = "http://127.0.0.1:9160";

    // Joins the pretty-printed JSON response onto one line.
    static String compact(String json) {
        return json.replaceAll("\\n\\s*", "");
    }

    public static void main(String[] args) throws Exception {
        List<String> values = List.of("C++ & Java/Go", "café", "50% off", "~user*(1)!");

        System.out.println("URLEncoder.encode(v, UTF_8):");
        for (String v : values) {
            String encoded = URLEncoder.encode(v, StandardCharsets.UTF_8);
            System.out.printf("  %-18s -> %s%n", "\"" + v + "\"", encoded);
        }

        System.out.println("URLEncoder output used in a path (+ replaced with %20):");
        String docName = "AB/12 café";
        String segment = URLEncoder.encode(docName, StandardCharsets.UTF_8).replace("+", "%20");
        System.out.println("  " + segment);

        System.out.println("new URI(scheme, authority, path, query, fragment):");
        URI uri = new URI("http", "127.0.0.1:9160", "/v2/docs/report", "tag=C++ & Java/Go", null);
        System.out.println("  " + uri.toASCIIString());

        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder(uri).build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println("  server got: " + compact(response.body()));

        String tag = URLEncoder.encode("C++ & Java/Go", StandardCharsets.UTF_8);
        URI fixed = URI.create(BASE + "/v2/docs/" + segment + "?tag=" + tag);
        response = client.send(HttpRequest.newBuilder(fixed).build(), HttpResponse.BodyHandlers.ofString());
        System.out.println("Encoded each value first:");
        System.out.println("  " + fixed.getRawPath() + "?" + fixed.getRawQuery());
        System.out.println("  server got: " + compact(response.body()));

        System.out.println("URLDecoder.decode(\"a+b%2Bc\", UTF_8): "
                + URLDecoder.decode("a+b%2Bc", StandardCharsets.UTF_8));
    }
}
