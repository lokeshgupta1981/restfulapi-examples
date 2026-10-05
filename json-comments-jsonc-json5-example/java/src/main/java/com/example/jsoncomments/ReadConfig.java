package com.example.jsoncomments;

import java.nio.file.Files;
import java.nio.file.Path;

import tools.jackson.core.JacksonException;
import tools.jackson.core.json.JsonReadFeature;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

public class ReadConfig {

  public static void main(String[] args) throws Exception {
    String jsonc = Files.readString(Path.of("..", "config", "orders-service.jsonc"));

    // A default JsonMapper follows RFC 8259 and rejects comments.
    JsonMapper strictMapper = JsonMapper.builder().build();
    try {
      strictMapper.readTree(jsonc);
    } catch (JacksonException e) {
      System.out.println("Strict: " + e.getClass().getSimpleName() + ": " + e.getOriginalMessage());
    }
    String trailing = Files.readString(Path.of("..", "config", "trailing-comma.jsonc"));
    try {
      strictMapper.readTree(trailing);
    } catch (JacksonException e) {
      System.out.println("Strict, trailing comma: " + e.getClass().getSimpleName() + ": " + e.getOriginalMessage());
    }

    // This mapper accepts // and /* */ comments and trailing commas (JSONC).
    JsonMapper configMapper = JsonMapper.builder()
        .enable(JsonReadFeature.ALLOW_JAVA_COMMENTS)
        .enable(JsonReadFeature.ALLOW_TRAILING_COMMA)
        .build();
    JsonNode settings = configMapper.readTree(jsonc);
    System.out.println("JSONC: " + settings);
    System.out.println("maxAttempts = " + settings.at("/retry/maxAttempts").asInt());
  }
}
