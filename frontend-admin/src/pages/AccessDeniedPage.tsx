import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export function AccessDeniedPage() {
  return (
    <Result
      status="403"
      title="Нет доступа"
      subTitle="Вход разрешён только аккаунтам с флагом администратора (is_admin) или email/id из allowlist в настройках сервера."
      extra={
        <Link to="/login">
          <Button type="primary">На страницу входа</Button>
        </Link>
      }
    />
  )
}
