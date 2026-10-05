package net.restfulapi.reports;

import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ReportController {

  record Row(String region, int orders, String revenue) {}

  record SalesReport(String month, List<Row> rows) {}

  record Note(String text) {}

  // A class with private fields and no getters: Jackson finds no properties to write.
  static class HiddenReport {
    private final String month;

    HiddenReport(String month) {
      this.month = month;
    }
  }

  // Jackson is the only converter for this record, so Spring can send JSON only.
  @GetMapping("/reports/{month}")
  public SalesReport salesReport(@PathVariable String month) {
    return new SalesReport(month, List.of(
        new Row("north", 412, "18350.00"),
        new Row("south", 287, "12990.50")));
  }

  // produces limits this endpoint to XML, which no converter here can write.
  @GetMapping(path = "/xml-reports/{month}", produces = MediaType.APPLICATION_XML_VALUE)
  public SalesReport xmlReport(@PathVariable String month) {
    return salesReport(month);
  }

  @GetMapping("/hidden-reports/{month}")
  public HiddenReport hiddenReport(@PathVariable String month) {
    return new HiddenReport(month);
  }

  // Accept problems give HTTP 406; Content-Type problems give HTTP 415.
  @PostMapping(path = "/reports/{month}/notes", consumes = MediaType.APPLICATION_JSON_VALUE)
  @ResponseStatus(HttpStatus.CREATED)
  public Note addNote(@PathVariable String month, @RequestBody Note note) {
    return note;
  }
}
