package cn.edu.sdu.software.service;

import java.io.InputStream;

public interface MinioFileService {
    /**
     * 上传文件
     *
     * @param fileName 文件名
     * @param content  文件内容
     * @param contentType 文件类型
     * @return 文件的访问路径或标识
     */
    String uploadFile(String fileName, String content, String contentType);

    /**
     * 读取文件内容
     *
     * @param fileName 文件名
     * @return 文件内容的字符串表示
     */
    String getFileContent(String fileName);
}
