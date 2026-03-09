package cn.edu.sdu.software.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor

public class Connection {
    private String from;
    private String to;
    private String fromPort;
    private String toPort;
}
