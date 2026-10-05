import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

public class HttpClientDemo {
  public static void main(String[] args) throws Exception {
    HttpClient client = HttpClient.newBuilder()
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build();

    String userPass = "reports-app:demo-pass-123";
    String basicValue = "Basic " + Base64.getEncoder()
        .encodeToString(userPass.getBytes(StandardCharsets.UTF_8));
    HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:9771/echo"))
        .header("Authorization", basicValue)
        .build();
    HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
    System.out.println("Basic by hand   " + response.body());

    for (String target : new String[] {"to-same", "to-port", "to-host"}) {
      HttpRequest redirected = HttpRequest.newBuilder(URI.create("http://127.0.0.1:9771/" + target))
          .header("Authorization", "Bearer demo-token-123")
          .build();
      String body = client.send(redirected, HttpResponse.BodyHandlers.ofString()).body();
      System.out.println("redirect " + target + "  " + body);
    }
  }
}
