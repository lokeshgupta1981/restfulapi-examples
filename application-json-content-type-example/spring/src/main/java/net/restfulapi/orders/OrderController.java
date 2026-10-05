package net.restfulapi.orders;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

  record OrderIn(String item, int quantity) {}

  record OrderOut(int id, String item, int quantity) {}

  @PostMapping(path = "/orders", consumes = MediaType.APPLICATION_JSON_VALUE)
  @ResponseStatus(HttpStatus.CREATED)
  public OrderOut create(@RequestBody OrderIn order) {
    return new OrderOut(1001, order.item(), order.quantity());
  }
}
