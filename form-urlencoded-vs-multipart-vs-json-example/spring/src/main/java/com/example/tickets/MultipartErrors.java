package com.example.tickets;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MultipartException;

// Spring parses multipart bodies before it picks a controller method, so the
// handler must live in a @RestControllerAdvice. Without it, a multipart body
// without a boundary ends as HTTP 500.
@RestControllerAdvice
public class MultipartErrors {

    @ExceptionHandler(MultipartException.class)
    public ProblemDetail badMultipart(MultipartException e) {
        String reason = e.getMostSpecificCause().getMessage();
        return ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, reason);
    }
}
