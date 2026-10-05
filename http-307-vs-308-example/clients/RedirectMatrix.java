import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

// Send POST and PUT to /lab/<code> with java.net.http.HttpClient and print what reached /echo.
public class RedirectMatrix {
    static final String BASE = "http://127.0.0.1:9190";
    static final String ORDER = "{\"sku\": \"BOOK-42\", \"qty\": 2}";
    static final Pattern SUMMARY = Pattern.compile("\"summary\":\"([^\"]*)\"");

    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NORMAL)
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        for (String method : new String[] {"POST", "PUT"}) {
            for (int code : new int[] {301, 302, 303, 307, 308}) {
                System.out.println(String.format("%-4s %d -> %s", method, code,
                        send(client, method, BASE + "/lab/" + code)));
            }
        }
        System.out.println("POST 308 to another host -> " + send(client, "POST", BASE + "/lab/308?cross=1"));
    }

    static String send(HttpClient client, String method, String url) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer demo-token")
                .method(method, HttpRequest.BodyPublishers.ofString(ORDER))
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        Matcher matcher = SUMMARY.matcher(response.body());
        return matcher.find() ? matcher.group(1) : response.statusCode() + " " + response.body();
    }
}
