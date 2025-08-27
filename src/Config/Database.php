<?php

namespace App\Config;

use PDO;
use PDOException;
use Exception;
use Dotenv\Dotenv;

class Database
{
    private static ?PDO $connection = null;
    
    /**
     * Obtém a conexão com o banco de dados
     * 
     * @return PDO
     * @throws PDOException
     */
    public static function getConnection(): PDO
    {
        if (self::$connection === null) {
            self::$connection = self::createConnection();
        }
        
        return self::$connection;
    }
    
    /**
     * Cria uma nova conexão com o banco de dados
     * 
     * @return PDO
     * @throws PDOException
     */
    private static function createConnection(): PDO
    {
        // Carrega as variáveis de ambiente se o arquivo .env existir
        $envPath = __DIR__ . '/../../.env';
        if (file_exists($envPath)) {
            try {
                $dotenv = Dotenv::createImmutable(__DIR__ . '/../../');
                $dotenv->load();
            } catch (Exception $e) {
                // Se não conseguir carregar o .env, usa valores padrão
            }
        }
        
        // Valores padrão para desenvolvimento local
        $host = $_ENV['DB_HOST'] ?? 'localhost';
        $dbname = $_ENV['DB_NAME'] ?? 'andreia';
        $username = $_ENV['DB_USER'] ?? 'root';
        $password = $_ENV['DB_PASS'] ?? '';
        
        $dsn = "mysql:host={$host};dbname={$dbname};charset=utf8mb4";
        
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
        ];
        
        try {
            return new PDO($dsn, $username, $password, $options);
        } catch (PDOException $e) {
            throw new PDOException("Erro na conexão com o banco de dados: " . $e->getMessage());
        }
    }
    
    /**
     * Executa uma query e retorna o resultado
     * 
     * @param string $sql
     * @param array $params
     * @return array
     */
    public static function query(string $sql, array $params = []): array
    {
        try {
            $pdo = self::getConnection();
            $stmt = $pdo->prepare($sql);
            $stmt->execute($params);
            return $stmt->fetchAll();
        } catch (PDOException $e) {
            throw new PDOException("Erro na execução da query: " . $e->getMessage());
        }
    }
    
    /**
     * Executa uma query e retorna uma única linha
     * 
     * @param string $sql
     * @param array $params
     * @return array|null
     */
    public static function queryOne(string $sql, array $params = []): ?array
    {
        try {
            $pdo = self::getConnection();
            $stmt = $pdo->prepare($sql);
            $stmt->execute($params);
            $result = $stmt->fetch();
            return $result ?: null;
        } catch (PDOException $e) {
            throw new PDOException("Erro na execução da query: " . $e->getMessage());
        }
    }
    
    /**
     * Executa uma query de inserção, atualização ou exclusão
     * 
     * @param string $sql
     * @param array $params
     * @return int Número de linhas afetadas
     */
    public static function execute(string $sql, array $params = []): int
    {
        try {
            $pdo = self::getConnection();
            $stmt = $pdo->prepare($sql);
            $stmt->execute($params);
            return $stmt->rowCount();
        } catch (PDOException $e) {
            throw new PDOException("Erro na execução da query: " . $e->getMessage());
        }
    }
    
    /**
     * Obtém o último ID inserido
     * 
     * @return string
     */
    public static function lastInsertId(): string
    {
        return self::getConnection()->lastInsertId();
    }
    
    /**
     * Inicia uma transação
     */
    public static function beginTransaction(): void
    {
        self::getConnection()->beginTransaction();
    }
    
    /**
     * Confirma uma transação
     */
    public static function commit(): void
    {
        self::getConnection()->commit();
    }
    
    /**
     * Reverte uma transação
     */
    public static function rollback(): void
    {
        self::getConnection()->rollback();
    }
    
    /**
     * Método de compatibilidade com a implementação anterior
     * 
     * @return PDO
     * @deprecated Use getConnection() instead
     */
    public static function getInstance()
    {
        return self::getConnection();
    }
}