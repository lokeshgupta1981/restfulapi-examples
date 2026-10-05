import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

// Java HttpClient on a never-ending redirect chain: what does send() return?
public class LoopCheck {
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newBuilder()
                .followRedirects(HttpClient.Redirect.NORMAL)
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:9190/loop/0")).build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println("Java HttpClient: returned HTTP " + response.statusCode() + " from " + response.uri().getPath());
    }
}
