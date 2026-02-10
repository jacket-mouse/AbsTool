package cn.edu.sdu.software.service;

import cn.edu.sdu.software.dto.LoginDto;
import cn.edu.sdu.software.dto.RegisterDto;

public interface UserService {
    LoginDto.LoginResponse login(LoginDto.LoginRequest request);
    void register(RegisterDto.RegisterRequest request);
}
