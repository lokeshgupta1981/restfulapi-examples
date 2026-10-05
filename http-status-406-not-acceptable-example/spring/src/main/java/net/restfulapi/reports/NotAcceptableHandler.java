package net.restfulapi.reports;

import jakarta.servlet.http.HttpServletRequest;
import java.net.URI;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpMediaTypeNotAcceptableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

// Turned on with reports.custom-406=true, so the demo can show both the built-in and the custom body.
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
@ConditionalOnProperty(name = "reports.custom-406", havingValue = "true")
public class NotAcceptableHandler {

  @ExceptionHandler(HttpMediaTypeNotAcceptableException.class)
  public ResponseEntity<ProblemDetail> notAcceptable(
      HttpMediaTypeNotAcceptableException exception, HttpServletRequest request) {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(
        HttpStatus.NOT_ACCEPTABLE,
        "No available format matches Accept: " + request.getHeader("Accept"));
    problem.setType(URI.create("https://example.com/problems/not-acceptable"));
    problem.setTitle("Not Acceptable");
    List<Map<String, String>> available = exception.getSupportedMediaTypes().stream()
        .map(mediaType -> Map.of("type", mediaType.toString(), "href", request.getRequestURI()))
        .toList();
    problem.setProperty("available", available);
    return ResponseEntity.status(HttpStatus.NOT_ACCEPTABLE)
        .contentType(MediaType.APPLICATION_PROBLEM_JSON)
        .header("Vary", "Accept")
        .body(problem);
  }
}
