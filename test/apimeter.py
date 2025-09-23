from locust import HttpUser, task, between


from quark import Task
# Task.URL = 'http://172.16.1.251:8657'
# tmgr = Task('p3gs`IpuBxTZb.RgzR9VrRmJKHyordg5tUKD87BmbUy/:K{N6lUN5JkM2hUP6VUN5N{OypkJxiY[jxjJ2BkP{FkPzJEJxNUMzFUM1JENzJjPjRYZqKDMj53ZvNXZvNYbyGnZBWo[iWYdjpkJzW3d2Kzf')
token = 'lJGJTerI3lBttE.yJNvjBnWz7wstblYTzk[6omgfPEp/Rg3JkNzlEOvlUO6BkO4BkO4FkPjBIfmKDMjlUO7VUN7JUNhhUNulENuVkNxJkJ7JDeimnJtJkPjxX[3WHcjxjJvOnMkGnM{mXdiKHRtm4[vWn[jpkJzW3d2Kzf'
tmgr = Task(token)  # 2506260046385625657
# tmgr.verify()


class FastAPIUser(HttpUser):
    # 模拟用户请求之间的等待时间：1 到 2 秒
    wait_time = between(0, 0.02)

    @task
    def get_test_endpoint(self):
        # 替换为你的实际接口路径
        self.client.get("https://quafu-sqc.baqis.ac.cn/task/-9")
        # tmgr.status()

    # @task(2)
    def get_items(self):
        """频率为 2 的 GET 请求"""
        # headers = {"Authorization": f"Bearer {token}"}  # if self.token else {}
        headers = {'token': self.token}
        self.client.get("/items", headers=headers)

    # 示例：POST 请求
    # @task
    # def post_data(self):
    #     self.client.post("/your-post-endpoint", json={"key": "value"})
