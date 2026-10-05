package com.example.orders;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class BulkCancelController {

  record Item(String orderId) {}
  record BulkCancelRequest(List<Item> items) {}
  record Result(int index, String orderId, int status, String detail) {}
  record Summary(int succeeded, int failed) {}
  record BulkCancelResponse(List<Result> results, Summary summary) {}

  private final Map<String, String> orderStates = new ConcurrentHashMap<>(
      Map.of("ord-1001", "pending", "ord-1002", "shipped", "ord-1003", "pending"));

  @PostMapping("/orders/bulk-cancel")
  public ResponseEntity<BulkCancelResponse> bulkCancel(@RequestBody BulkCancelRequest request) {
    List<Result> results = new ArrayList<>();
    for (int index = 0; index < request.items().size(); index++) {
      String orderId = request.items().get(index).orderId();
      String state = orderStates.get(orderId);
      if (state == null) {
        results.add(new Result(index, orderId, 404, "Order " + orderId + " does not exist."));
      } else if (state.equals("shipped")) {
        results.add(new Result(index, orderId, 409, "Order " + orderId + " has already shipped."));
      } else {
        orderStates.put(orderId, "cancelled");
        results.add(new Result(index, orderId, 200, "Order " + orderId + " is cancelled."));
      }
    }
    int succeeded = (int) results.stream().filter(result -> result.status() < 300).count();
    BulkCancelResponse body = new BulkCancelResponse(results, new Summary(succeeded, results.size() - succeeded));
    return ResponseEntity.status(HttpStatus.MULTI_STATUS).body(body);
  }
}
