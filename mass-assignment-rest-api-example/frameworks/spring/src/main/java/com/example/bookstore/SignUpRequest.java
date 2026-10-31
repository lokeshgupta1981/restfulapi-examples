package com.example.bookstore;

// The DTO: only the fields a new user may send.
public record SignUpRequest(String email, String name, String password) {
}
