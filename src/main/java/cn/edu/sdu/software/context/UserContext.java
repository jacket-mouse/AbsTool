package cn.edu.sdu.software.context;

/**
 * 使用 ThreadLocal 存储当前请求的用户上下文
 */
public class UserContext {

    private static final ThreadLocal<String> USER_HOLDER = new ThreadLocal<>();

    public static void setUserId(String userId) {
        USER_HOLDER.set(userId);
    }

    public static String getUserId() {
        return USER_HOLDER.get();
    }

    public static void clear() {
        USER_HOLDER.remove();
    }
}
