import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

public class UrlBuilding {
    static final String BASE = "http://127.0.0.1:9160";

    public static void main(String[] args) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newHttpClient();

        URI broken;
        try {
            broken = new URI("http", "127.0.0.1:9160", "/v2/docs/report", "tag=C++ & Java/Go", null);
        } catch (URISyntaxException e) {
            throw new IllegalArgumentException("Cannot build the URI", e);
        }

        String docName = "AB/12 café";
        String segment = URLEncoder.encode(docName, StandardCharsets.UTF_8).replace("+", "%20");
        String tag = URLEncoder.encode("C++ & Java/Go", StandardCharsets.UTF_8);
        URI fixed = URI.create(BASE + "/v2/docs/" + segment + "?tag=" + tag);

        for (URI uri : new URI[] {broken, fixed}) {
            HttpResponse<String> response = client.send(
                    HttpRequest.newBuilder(uri).build(), HttpResponse.BodyHandlers.ofString());
            System.out.println(uri.getRawPath() + "?" + uri.getRawQuery());
            System.out.println("  " + response.body().replaceAll("\\n\\s*", ""));
        }
    }
}
