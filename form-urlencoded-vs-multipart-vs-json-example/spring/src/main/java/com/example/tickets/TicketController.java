package com.example.tickets;

import java.io.IOException;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class TicketController {

    public record Customer(String id, String plan) {}

    public record TicketJson(String subject, String priority, List<String> tags, Customer customer) {}

    public record TicketForm(String subject, String priority, List<String> tags) {}

    @PostMapping(path = "/tickets", consumes = MediaType.APPLICATION_JSON_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> fromJson(@RequestBody TicketJson ticket) {
        return Map.of("parsedAs", "json", "ticket", ticket);
    }

    @PostMapping(path = "/tickets", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> fromForm(@ModelAttribute TicketForm ticket) {
        requireSubject(ticket);
        return Map.of("parsedAs", "form", "ticket", ticket);
    }

    @PostMapping(path = "/tickets", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> fromMultipart(@ModelAttribute TicketForm ticket,
                                             @RequestPart("attachment") MultipartFile attachment) throws IOException {
        requireSubject(ticket);
        Map<String, Object> file = Map.of(
                "filename", attachment.getOriginalFilename(),
                "contentType", attachment.getContentType(),
                "size", attachment.getBytes().length);
        return Map.of("parsedAs", "multipart", "ticket", ticket, "attachment", file);
    }

    // Nested JSON and a file in one request: the JSON goes in its own part.
    @PostMapping(path = "/tickets/with-attachment", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> jsonPartAndFile(@RequestPart("ticket") TicketJson ticket,
                                               @RequestPart("attachment") MultipartFile attachment) {
        return Map.of("parsedAs", "multipart with a JSON part", "ticket", ticket,
                "attachmentSize", attachment.getSize());
    }

    // Form binding leaves missing fields null, so a JSON body sent as a form arrives "empty".
    private static void requireSubject(TicketForm ticket) {
        if (ticket.subject() == null || ticket.subject().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "Field 'subject' is required");
        }
    }
}
