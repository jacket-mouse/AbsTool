package cn.edu.sdu.software.controller;

import cn.edu.sdu.software.dto.LoginDto;
import cn.edu.sdu.software.dto.RegisterDto;
import cn.edu.sdu.software.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private UserService userService;

    @PostMapping("/login")
    public LoginDto.LoginResponse login(@RequestBody LoginDto.LoginRequest request) {
        return userService.login(request);
    }

    @PostMapping("/register")
    public String register(@RequestBody RegisterDto.RegisterRequest request) {
        userService.register(request);
        return "注册成功";
    }
}
