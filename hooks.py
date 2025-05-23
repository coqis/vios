# https://www.mkdocs.org/user-guide/configuration/#hooks


from mkdocs.config.config_options import Type
from mkdocs.plugins import BasePlugin
import os
import shutil
from pathlib import Path

import quark.driver

sitepath = Path(quark.driver.__file__).parents[2]

src = [p.name for p in (Path(__file__).parent / 'quark').iterdir()]


class CustomPlugin(BasePlugin):
    config_scheme = (
        ('pre_message', Type(str, default='')),
        ('post_message', Type(str, default='')))

    def on_pre_build(self, config):
        """构建开始前执行"""
        print(f"Pre-build: {self.config['pre_message']}")
        # 自定义操作（如清理临时文件）
        return config

    def on_post_build(self, config):
        """构建完成后执行"""
        print(f"Post-build: {self.config['post_message']}")
        # 自定义操作（如压缩输出文件）


def on_pre_build(config):
    print("构建前操作：备份文档")

    try:
        shutil.copytree('quark', sitepath / 'quark', dirs_exist_ok=True)
        [print('+' * 24, p) for p in src]
    except Exception as e:
        print('>' * 48, e)


def on_post_build(config):
    print("构建后操作：生成索引")

    try:
        for p in (sitepath / 'quark').iterdir():
            if p.name in src:
                try:
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
                except Exception as e:
                    print('<' * 48, e)
                print('-' * 24, p.name)
    except Exception as e:
        print('>' * 48, e)
