package com.example.bookstore;

import java.util.concurrent.atomic.AtomicLong;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    private final AtomicLong ids = new AtomicLong(1);

    // Vulnerable: Jackson calls every setter that matches a JSON key
    @PostMapping("/vulnerable/users")
    @ResponseStatus(HttpStatus.CREATED)
    public User signUpVulnerable(@RequestBody User user) {
        user.setId(ids.incrementAndGet());
        return user;
    }

    // Fixed: bind to the DTO, then copy the allowed fields ourselves
    @PostMapping("/users")
    @ResponseStatus(HttpStatus.CREATED)
    public User signUp(@RequestBody SignUpRequest request) {
        User user = new User();
        user.setId(ids.incrementAndGet());
        user.setEmail(request.email());
        user.setName(request.name());
        user.setPassword(request.password());
        return user;
    }
}
