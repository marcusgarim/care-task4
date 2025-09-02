<?php

namespace App\Services;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class CurrencyService
{
    private $client;
    private $db;
    
    public function __construct()
    {
        $this->client = new Client();
        $this->db = new DatabaseService();
    }
    
    /**
     * Obtém a taxa de câmbio atual do dólar para real
     * 
     * @return float Taxa de câmbio USD/BRL
     */
    public function getDollarToRealRate(): float
    {
        try {
            // Primeiro, tenta buscar de uma API gratuita
            $rate = $this->fetchFromAPI();
            
            if ($rate > 0) {
                // Salva a taxa no banco para cache
                $this->saveExchangeRate($rate);
                return $rate;
            }
            
            // Se falhar, usa a taxa salva no banco
            $cachedRate = $this->getCachedExchangeRate();
            if ($cachedRate > 0) {
                return $cachedRate;
            }
            
            // Fallback: taxa fixa de 5.00 (valor conservador)
            error_log("CurrencyService: Usando taxa de câmbio padrão (5.00)");
            return 5.00;
            
        } catch (\Exception $e) {
            error_log("CurrencyService: Erro ao obter taxa de câmbio: " . $e->getMessage());
            
            // Tenta usar taxa em cache
            $cachedRate = $this->getCachedExchangeRate();
            if ($cachedRate > 0) {
                return $cachedRate;
            }
            
            // Fallback final
            return 5.00;
        }
    }
    
    /**
     * Busca taxa de câmbio de uma API gratuita
     */
    private function fetchFromAPI(): float
    {
        try {
            // API gratuita do Banco Central do Brasil
            $response = $this->client->get('https://economia.awesomeapi.com.br/last/USD-BRL', [
                'timeout' => 5,
                'headers' => [
                    'User-Agent' => 'Andreia32/1.0'
                ]
            ]);
            
            $data = json_decode($response->getBody(), true);
            
            if (isset($data['USDBRL']['bid'])) {
                $rate = (float) $data['USDBRL']['bid'];
                error_log("CurrencyService: Taxa obtida da API: $rate");
                return $rate;
            }
            
            return 0;
            
        } catch (RequestException $e) {
            error_log("CurrencyService: Erro na API de câmbio: " . $e->getMessage());
            return 0;
        }
    }
    
    /**
     * Salva a taxa de câmbio no banco de dados
     */
    private function saveExchangeRate(float $rate): void
    {
        try {
            $sql = "INSERT INTO configuracoes (chave, valor, updated_at) 
                    VALUES ('taxa_cambio_usd_brl', ?, NOW()) 
                    ON DUPLICATE KEY UPDATE valor = ?, updated_at = NOW()";
            
            $this->db->execute($sql, [$rate, $rate]);
            error_log("CurrencyService: Taxa de câmbio salva: $rate");
            
        } catch (\Exception $e) {
            error_log("CurrencyService: Erro ao salvar taxa de câmbio: " . $e->getMessage());
        }
    }
    
    /**
     * Obtém a taxa de câmbio salva no banco
     */
    private function getCachedExchangeRate(): float
    {
        try {
            $sql = "SELECT valor FROM configuracoes WHERE chave = 'taxa_cambio_usd_brl'";
            $result = $this->db->query($sql);
            
            if (!empty($result)) {
                $rate = (float) $result[0]['valor'];
                error_log("CurrencyService: Taxa de câmbio em cache: $rate");
                return $rate;
            }
            
            return 0;
            
        } catch (\Exception $e) {
            error_log("CurrencyService: Erro ao buscar taxa em cache: " . $e->getMessage());
            return 0;
        }
    }
    
    /**
     * Converte valor de dólares para reais
     */
    public function convertDollarToReal(float $dollarAmount): float
    {
        $rate = $this->getDollarToRealRate();
        return $dollarAmount * $rate;
    }
    
    /**
     * Formata valor em reais
     */
    public function formatReal(float $value): string
    {
        return 'R$ ' . number_format($value, 2, ',', '.');
    }
}
