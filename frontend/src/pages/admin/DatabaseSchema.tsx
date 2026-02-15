import { useEffect, useState } from 'react'
import axios from 'axios'
import Layout from '../../components/Layout'
import api from '../../utils/api'
import type { ApiErrorResponse } from '../../types/models'

interface ColumnInfo {
  name: string
  type: string
  nullable: boolean
  default: string
  autoincrement: boolean
}

interface ForeignKeyInfo {
  constrained_columns: string[]
  referred_table: string
  referred_columns: string[]
}

interface IndexInfo {
  name: string
  columns: string[]
  unique: boolean
}

interface TableInfo {
  name: string
  columns: ColumnInfo[]
  primary_keys: string[]
  foreign_keys: ForeignKeyInfo[]
  indexes: IndexInfo[]
}

interface SchemaResponse {
  success: boolean
  tables?: Record<string, TableInfo>
  table_count?: number
  error?: string
}

interface ExampleRow {
  [key: string]: string | number | boolean | null | unknown
}

interface ExamplesResponse {
  success: boolean
  table?: string
  columns?: string[]
  examples?: ExampleRow[]
  error?: string
}

export default function AdminDatabaseSchema(): JSX.Element {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [schema, setSchema] = useState<Record<string, TableInfo>>({})
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [loadingExamples, setLoadingExamples] = useState(false)
  const [examples, setExamples] = useState<ExamplesResponse | null>(null)

  useEffect(() => {
    void loadSchema()
  }, [])

  const loadSchema = async (): Promise<void> => {
    try {
      setLoading(true)
      setError('')
      const res = await api.get<SchemaResponse>('/admin/dashboard/database-schema/data')
      if (res.data.success && res.data.tables) {
        setSchema(res.data.tables)
        if (res.data.table_count && res.data.table_count > 0) {
          setSelectedTable(Object.keys(res.data.tables)[0])
        }
      } else {
        setError(res.data.error || 'Ошибка загрузки структуры базы данных')
      }
    } catch (err: unknown) {
      let message = 'Ошибка загрузки структуры базы данных'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const loadExamples = async (): Promise<void> => {
    if (!selectedTable) return
    try {
      setLoadingExamples(true)
      setError('')
      const res = await api.get<ExamplesResponse>(`/admin/dashboard/database-schema/examples?table=${encodeURIComponent(selectedTable)}`)
      if (res.data.success) {
        setExamples(res.data)
      } else {
        setError(res.data.error || 'Ошибка загрузки примеров')
      }
    } catch (err: unknown) {
      let message = 'Ошибка загрузки примеров'
      if (axios.isAxiosError<ApiErrorResponse>(err)) {
        message = err.response?.data?.error || err.message || message
      }
      setError(message)
    } finally {
      setLoadingExamples(false)
    }
  }

  const table = selectedTable ? schema[selectedTable] : null

  return (
    <Layout title="Структура базы данных" isAdmin>
      <div className="database-schema-page">
        {loading ? (
          <div className="loading">Загрузка структуры базы данных...</div>
        ) : error ? (
          <div className="alert alert-error">{error}</div>
        ) : (
          <div className="schema-container" style={{ display: 'flex', gap: '20px' }}>
            <div className="tables-list" style={{ width: '250px', flexShrink: 0 }}>
              <h3>Таблицы ({Object.keys(schema).length})</h3>
              <div className="table-list" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                {Object.keys(schema).map((tableName) => (
                  <div
                    key={tableName}
                    onClick={() => {
                      setSelectedTable(tableName)
                      setExamples(null)
                    }}
                    style={{
                      padding: '10px',
                      cursor: 'pointer',
                      backgroundColor: selectedTable === tableName ? '#e3f2fd' : 'transparent',
                      border: '1px solid #ddd',
                      marginBottom: '5px',
                      borderRadius: '4px',
                    }}
                  >
                    <strong>{tableName}</strong>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {schema[tableName].columns.length} колонок
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="table-details" style={{ flex: 1 }}>
              {table ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2>{table.name}</h2>
                    <button
                      onClick={() => void loadExamples()}
                      disabled={loadingExamples}
                      className="btn btn-primary"
                      style={{ marginLeft: '20px' }}
                    >
                      {loadingExamples ? 'Загрузка...' : 'Получить пример'}
                    </button>
                  </div>

                  <div className="card" style={{ marginBottom: '20px' }}>
                    <h3>Колонки ({table.columns.length})</h3>
                    <table className="table" style={{ width: '100%' }}>
                      <thead>
                        <tr>
                          <th>Имя</th>
                          <th>Тип</th>
                          <th>Nullable</th>
                          <th>Default</th>
                          <th>Autoincrement</th>
                        </tr>
                      </thead>
                      <tbody>
                        {table.columns.map((col) => (
                          <tr key={col.name}>
                            <td>
                              <strong>{col.name}</strong>
                              {table.primary_keys.includes(col.name) && (
                                <span style={{ marginLeft: '5px', color: '#1976d2' }}>🔑</span>
                              )}
                            </td>
                            <td>{col.type}</td>
                            <td>{col.nullable ? 'Да' : 'Нет'}</td>
                            <td>{col.default}</td>
                            <td>{col.autoincrement ? 'Да' : 'Нет'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {table.foreign_keys.length > 0 && (
                    <div className="card" style={{ marginBottom: '20px' }}>
                      <h3>Внешние ключи ({table.foreign_keys.length})</h3>
                      <table className="table" style={{ width: '100%' }}>
                        <thead>
                          <tr>
                            <th>Колонки</th>
                            <th>Ссылается на таблицу</th>
                            <th>Колонки в таблице</th>
                          </tr>
                        </thead>
                        <tbody>
                          {table.foreign_keys.map((fk, idx) => (
                            <tr key={idx}>
                              <td>{fk.constrained_columns.join(', ')}</td>
                              <td>{fk.referred_table}</td>
                              <td>{fk.referred_columns.join(', ')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {table.indexes.length > 0 && (
                    <div className="card">
                      <h3>Индексы ({table.indexes.length})</h3>
                      <table className="table" style={{ width: '100%' }}>
                        <thead>
                          <tr>
                            <th>Имя</th>
                            <th>Колонки</th>
                            <th>Уникальный</th>
                          </tr>
                        </thead>
                        <tbody>
                          {table.indexes.map((idx) => (
                            <tr key={idx.name}>
                              <td>{idx.name}</td>
                              <td>{idx.columns.join(', ')}</td>
                              <td>{idx.unique ? 'Да' : 'Нет'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {examples && examples.examples && examples.examples.length > 0 && (
                    <div className="card" style={{ marginTop: '20px' }}>
                      <h3>Примеры данных (2 случайных записи)</h3>
                      {examples.examples.map((example, idx) => (
                        <div key={idx} style={{ marginBottom: '30px', border: '1px solid #ddd', padding: '15px', borderRadius: '8px' }}>
                          <h4 style={{ marginTop: 0, marginBottom: '15px' }}>Запись #{idx + 1}</h4>
                          <table className="table" style={{ width: '100%' }}>
                            <thead>
                              <tr>
                                <th>Параметр</th>
                                <th>Значение</th>
                              </tr>
                            </thead>
                            <tbody>
                              {examples.columns?.map((colName) => (
                                <tr key={colName}>
                                  <td><strong>{colName}</strong></td>
                                  <td>
                                    {example[colName] === null || example[colName] === undefined ? (
                                      <span style={{ color: '#999', fontStyle: 'italic' }}>NULL</span>
                                    ) : typeof example[colName] === 'object' ? (
                                      <pre style={{ margin: 0, fontSize: '12px', maxWidth: '500px', overflow: 'auto' }}>
                                        {JSON.stringify(example[colName], null, 2)}
                                      </pre>
                                    ) : (
                                      String(example[colName])
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div>Выберите таблицу для просмотра деталей</div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

