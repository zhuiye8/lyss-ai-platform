# 测试数据种子文件

这个目录包含开发和测试环境的初始数据。

## 文件说明

- `01-base-data.sql` - 基础数据（角色、租户等）
- `02-auth-data.sql` - 认证相关测试数据
- `03-provider-data.sql` - Provider测试Channel和配额数据

## 使用方法

```bash
# 开发环境自动加载（通过docker-compose）
docker-compose up -d

# 手动执行特定seed文件
psql -h localhost -p 5433 -U lyss -d lyss_db -f sql/seeds/01-base-data.sql
```

## 注意事项

- 生产环境请勿执行这些seed文件
- 包含测试账户和API密钥，仅用于开发