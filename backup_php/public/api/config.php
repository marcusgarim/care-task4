<?php
/**
 * Configurações de timeout para evitar respostas incompletas
 */

// Configurações de timeout do PHP
set_time_limit(120); // 2 minutos
ini_set('max_execution_time', 120);
ini_set('max_input_time', 120);
ini_set('memory_limit', '256M');
ini_set('post_max_size', '50M');
ini_set('upload_max_filesize', '50M');

// Configurações de sessão
ini_set('session.gc_maxlifetime', 3600); // 1 hora
ini_set('session.cookie_lifetime', 3600); // 1 hora

// Configurações de buffer
ini_set('output_buffering', 'On');
ini_set('implicit_flush', 'Off');

// Configurações de erro
error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);

// Configurações de timezone
date_default_timezone_set('America/Sao_Paulo');
