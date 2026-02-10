package cn.edu.sdu.software.service.impl;

import cn.edu.sdu.software.dto.LoginDto;
import cn.edu.sdu.software.dto.RegisterDto;
import cn.edu.sdu.software.entity.SysUser;
import cn.edu.sdu.software.mapper.SysUserMapper;
import cn.edu.sdu.software.service.UserService;
import cn.edu.sdu.software.utils.JwtUtils;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private SysUserMapper sysUserMapper;

    @Autowired
    private JwtUtils jwtUtils;

    // 使用 BCrypt 进行密码加密
    private final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Override
    public LoginDto.LoginResponse login(LoginDto.LoginRequest request) {
        // 1. 根据用户名查询用户
        QueryWrapper<SysUser> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", request.getUsername());
        SysUser user = sysUserMapper.selectOne(queryWrapper);

        // 2. 校验用户是否存在
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }

        // 3. 校验密码 (使用 matches 方法比较明文密码和加密后的密码)
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
             throw new RuntimeException("密码错误");
        }

        // 4. 生成 Token
        String token = jwtUtils.generateToken(user.getUserId(), user.getUsername());

        // 5. 返回结果
        return new LoginDto.LoginResponse(token, user.getUserId(), user.getUsername(), user.getNickname());
    }

    @Override
    @Transactional
    public void register(RegisterDto.RegisterRequest request) {
        // 1. 检查用户名是否存在
        QueryWrapper<SysUser> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("username", request.getUsername());
        if (sysUserMapper.selectCount(queryWrapper) > 0) {
            throw new RuntimeException("用户名已存在");
        }

        // 2. 创建用户
        SysUser user = new SysUser();
        user.setUserId(java.util.UUID.randomUUID().toString().replace("-", ""));
        user.setUsername(request.getUsername());
        // 加密密码
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setNickname(request.getNickname());
        user.setCreateTime(java.time.LocalDateTime.now());

        sysUserMapper.insert(user);
    }
}
