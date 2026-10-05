import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;

// Older java.net.HttpURLConnection: which redirects does it follow?
public class UrlConnectionCheck {
    public static void main(String[] args) throws Exception {
        String order = "{\"sku\": \"BOOK-42\", \"qty\": 2}";
        for (String method : new String[] {"GET", "POST", "PUT"}) {
            for (int code : new int[] {301, 302, 307, 308}) {
                URI uri = URI.create("http://127.0.0.1:9190/lab/" + code);
                HttpURLConnection connection = (HttpURLConnection) uri.toURL().openConnection();
                connection.setRequestMethod(method);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setRequestProperty("Authorization", "Bearer demo-token");
                if (!method.equals("GET")) {
                    connection.setDoOutput(true);
                    try (OutputStream out = connection.getOutputStream()) {
                        out.write(order.getBytes());
                    }
                }
                int status = connection.getResponseCode();
                String body = "";
                if (status == 200) {
                    try (InputStream in = connection.getInputStream()) {
                        String json = new String(in.readAllBytes());
                        body = json.substring(json.indexOf(":\"") + 2, json.indexOf("\","));
                    }
                }
                System.out.println(String.format("%-4s %d -> HTTP %d from %s  %s",
                        method, code, status, connection.getURL().getPath(), body));
            }
        }
    }
}
