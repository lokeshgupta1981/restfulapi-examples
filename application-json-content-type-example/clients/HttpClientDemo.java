import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class HttpClientDemo {
  public static void main(String[] args) throws Exception {
    HttpClient client = HttpClient.newHttpClient();
    String body = "{\"item\":\"keyboard\",\"quantity\":2}";

    HttpRequest noHeader = HttpRequest.newBuilder(URI.create("http://127.0.0.1:9300/orders"))
        .header("X-Client", "HttpClient, no Content-Type")
        .POST(HttpRequest.BodyPublishers.ofString(body))
        .build();
    System.out.println(client.send(noHeader, HttpResponse.BodyHandlers.ofString()).body());

    HttpRequest withHeader = HttpRequest.newBuilder(URI.create("http://127.0.0.1:9300/orders"))
        .header("X-Client", "HttpClient, headers set")
        .header("Content-Type", "application/json")
        .header("Accept", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(body))
        .build();
    System.out.println(client.send(withHeader, HttpResponse.BodyHandlers.ofString()).body());
  }
}
