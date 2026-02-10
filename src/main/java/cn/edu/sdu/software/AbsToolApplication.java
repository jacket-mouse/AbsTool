package cn.edu.sdu.software;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("cn.edu.sdu.software.mapper")
public class AbsToolApplication {
    public static void main(String[] args) {
        SpringApplication.run(AbsToolApplication.class, args);
    }
}