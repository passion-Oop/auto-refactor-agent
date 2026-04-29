# AutoRefactor Agent 🤖

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

一个智能的自动化代码重构代理，能够扫描、修复和验证代码质量，并自动创建Pull Request。

## 🚀 核心功能

- **代码质量扫描**：使用flake8/ruff/pylint检测代码问题
- **自动重构**：通过black、isort和ruff --fix自动修复代码风格问题
- **测试验证**：运行pytest确保重构不会破坏功能
- **自动化PR流程**：自动创建分支、提交更改并通过GitHub API创建Pull Request

## 🛠️ 技术栈

- **Python 3.7+**
- **GitPython**：Git操作自动化
- **Requests**：GitHub API交互
- **代码质量工具**：flake8, ruff, black, isort, pytest

## 📋 使用示例

```bash
export GITHUB_TOKEN="ghp_xxx"
python3 auto_refactor_agent.py \
    --repo-path /path/to/repo \
    --github-owner myorg \
    --github-repo myrepo \
    --base-branch main
```

## ⚠️ 重要提示

- **生产环境使用前**：请补充完善的安全机制、并发控制和回滚逻辑
- **依赖安装**：确保已安装所有必需的工具（可通过`pip install -r requirements.txt`安装）
- **权限要求**：需要GitHub token具有仓库写入权限

## 🎯 适用场景

- 大型代码库的自动化代码风格统一
- 持续集成/持续部署（CI/CD）流水线中的代码质量保障
- 团队协作中的代码规范自动化维护
- 技术债务的渐进式清理

## 🤝 贡献指南

欢迎提交Issue和Pull Request！建议在贡献前先讨论大型功能变更。

---

这个工具旨在作为起点和参考实现，您可以根据团队需求进行定制和扩展。
