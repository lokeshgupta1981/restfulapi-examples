package net.restfulapi.authheader;

import java.security.Principal;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrdersController {

  @GetMapping({"/basic/orders", "/bearer/orders"})
  public Map<String, Object> orders(Principal principal) {
    return Map.of("user", principal.getName(), "orders", List.of(1001, 1002));
  }
}
