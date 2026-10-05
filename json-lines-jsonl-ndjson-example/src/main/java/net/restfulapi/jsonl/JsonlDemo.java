package net.restfulapi.jsonl;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SequenceWriter;

import java.io.BufferedReader;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.stream.Stream;

public class JsonlDemo {

  @JsonInclude(JsonInclude.Include.NON_NULL)
  public record Order(String id, String customer, double total, String status, String note) {}

  private static final ObjectMapper MAPPER = new ObjectMapper();

  public static void main(String[] args) throws Exception {
    readFile(Path.of("data/orders.jsonl"));
    readFile(Path.of("data/orders-bad.jsonl"));
    writeFile(Path.of("data/orders-java.jsonl"));
    if (args.length > 0 && args[0].equals("http")) {
      readStream();
    }
  }

  // Read one line at a time; a bad line is reported with its number and skipped.
  static void readFile(Path path) throws IOException {
    System.out.println("== " + path.getFileName());
    try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
      String line;
      int lineNo = 0;
      while ((line = reader.readLine()) != null) {
        lineNo++;
        if (line.isBlank()) {
          continue;
        }
        try {
          Order order = MAPPER.readValue(line, Order.class);
          System.out.println(lineNo + " " + order.id() + " " + order.total());
        } catch (JsonProcessingException e) {
          System.out.println(lineNo + " skipped: " + e.getClass().getSimpleName()
              + " at column " + e.getLocation().getColumnNr());
        }
      }
    }
  }

  // SequenceWriter with a newline separator writes one compact value per line.
  static void writeFile(Path path) throws IOException {
    List<Order> orders = List.of(
        new Order("ord_3001", "Hana", 15.0, "paid", null),
        new Order("ord_3002", "Ivo", 64.2, "pending", null));
    try (SequenceWriter writer = MAPPER.writer()
        .withRootValueSeparator("\n")
        .writeValues(path.toFile())) {
      writer.writeAll(orders);
    }
    Files.writeString(path, "\n", StandardCharsets.UTF_8, StandardOpenOption.APPEND);
    System.out.println("== wrote " + path.getFileName());
    System.out.print(Files.readString(path));
  }

  // BodyHandlers.ofLines() gives a Stream<String> that fills while the response arrives.
  static void readStream() throws Exception {
    System.out.println("== GET /orders/export");
    HttpClient client = HttpClient.newHttpClient();
    HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:9387/orders/export")).build();
    long start = System.nanoTime();
    HttpResponse<Stream<String>> response = client.send(request, HttpResponse.BodyHandlers.ofLines());
    try (Stream<String> lines = response.body()) {
      lines.filter(line -> !line.isBlank()).forEach(line -> {
        try {
          Order order = MAPPER.readValue(line, Order.class);
          System.out.printf("%.1fs %s %s%n", (System.nanoTime() - start) / 1e9, order.id(), order.status());
        } catch (JsonProcessingException e) {
          throw new RuntimeException(e);
        }
      });
    }
  }
}
