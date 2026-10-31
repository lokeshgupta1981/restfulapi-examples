package com.example.bookstore;

// The internal model. In a real app this would be a JPA @Entity.
public class User {
    private Long id;
    private String email;
    private String name;
    private String password;  // demo only: store a hash in real code
    private String role = "customer";
    private int storeCredit;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public void setPassword(String password) { this.password = password; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public int getStoreCredit() { return storeCredit; }
    public void setStoreCredit(int storeCredit) { this.storeCredit = storeCredit; }
}
