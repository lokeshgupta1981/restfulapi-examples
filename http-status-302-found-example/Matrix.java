import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

// Same test with java.net.http.HttpClient (Java 21). Run: java Matrix.java
public class Matrix {
    public static void main(String[] args) throws Exception {
        String baseUrl = args.length > 0 ? args[0] : "http://127.0.0.1:9182";
        HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();
        System.out.println("Java " + System.getProperty("java.version") + " HttpClient, Redirect.NORMAL");
        for (int code : new int[] {302, 303, 307}) {
            for (String method : new String[] {"POST", "PUT", "DELETE"}) {
                HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "/redirect/" + code))
                        .header("Content-Type", "application/json")
                        .method(method, HttpRequest.BodyPublishers.ofString("{\"amount\":\"49.90\"}"))
                        .build();
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                System.out.printf("%-8s%-8d%s%n", method, code, response.body());
            }
        }
    }
}
