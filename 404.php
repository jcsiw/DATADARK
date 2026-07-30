<!DOCTYPE html>
<html lang="pt-br" data-bs-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>404 - Página Não Encontrada</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body {
      background: linear-gradient(135deg, #0d0d0d, #1b1b1b);
      color: #00ffff;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      font-family: 'Segoe UI', sans-serif;
    }
    .container {
      text-align: center;
      animation: shake 0.8s infinite;
    }
    h1 {
      font-size: 7rem;
      font-weight: bold;
      text-shadow: 0 0 30px #00ffff;
    }
    h2 {
      font-size: 2rem;
      margin-bottom: 2rem;
      color: #ff3b3b;
    }
    a.btn {
      padding: 0.75rem 2rem;
      font-size: 1.1rem;
      text-transform: uppercase;
      transition: all 0.3s ease;
    }
    a.btn:hover {
      transform: scale(1.05);
      box-shadow: 0 0 20px #00ffff;
    }
    @keyframes shake {
      0% { transform: translateX(0); }
      25% { transform: translateX(-5px); }
      50% { transform: translateX(5px); }
      75% { transform: translateX(-5px); }
      100% { transform: translateX(0); }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>404</h1>
    <h2>PÁGINA NÃO ENCONTRADA</h2>
    <p>A página que você tentou acessar não existe ou foi removida.</p>
    <a href="index.php" class="btn btn-outline-light mt-3"><i class="bi bi-house"></i> Voltar ao site</a>
  </div>
</body>
</html>
