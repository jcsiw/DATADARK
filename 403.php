<!DOCTYPE html>
<html lang="pt-br" data-bs-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>403 - Acesso Negado</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    body {
      background: radial-gradient(circle at center, #1b1b1b, #0d0d0d);
      color: #ff3b3b;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      font-family: 'Segoe UI', sans-serif;
    }
    .container {
      text-align: center;
      animation: pulse 1.5s infinite alternate;
    }
    h1 {
      font-size: 6rem;
      font-weight: bold;
      text-shadow: 0 0 20px #ff3b3b;
    }
    h2 {
      font-size: 2rem;
      margin-bottom: 2rem;
    }
    a.btn {
      padding: 0.75rem 2rem;
      font-size: 1.1rem;
      text-transform: uppercase;
      transition: all 0.3s ease;
    }
    a.btn:hover {
      transform: scale(1.05);
      box-shadow: 0 0 20px #ff3b3b;
    }
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.02); }
      100% { transform: scale(1); }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>403</h1>
    <h2>ACESSO NEGADO</h2>
    <p>Sem permissão para acessar essa área ou seu acesso foi Bloqueado.</p>
    <a href="index.php" class="btn btn-outline-light mt-3"><i class="bi bi-arrow-left-circle"></i> Voltar ao site</a>
  </div>
</body>
</html>
