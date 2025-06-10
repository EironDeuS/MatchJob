Integrantes:
Aaron Muñoz
Miguel Vargas
Cristian Ruiz

https://github.com/EironDeuS/MatchJob.git

para subir ay que cambiar la linea del debug del seting a true.

1.
"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" builds submit --tag gcr.io/matchjob-458200/matchjob-app



2.
"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" run deploy matchjob-service --image gcr.io/matchjob-458200/matchjob-app --platform managed --region southamerica-west1 --allow-unauthenticated --update-env-vars SECRET_KEY="your-very-strong-and-random-secret-key-for-production",DJANGO_DEBUG="False",DB_NAME="BDmatchjob",DB_USER="neondb_owner",DB_PASSWORD="npg_lU8ucqsIiP6X",DB_HOST="ep-weathered-sunset-ac0mxs0q-pooler.sa-east-1.aws.neon.tech",DB_PORT="5432",EMAIL_HOST_USER="matchjobbeta@gmail.com",EMAIL_HOST_PASSWORD="rbxf vwqk yhxv yyxp",MAPBOX_TOKEN="pk.eyJuIjoiYWFtdW51b2JpLCJhIjoiY21hbjk0NTc2MHQwbjJ4b2ppcGtwcWVyYiJ9.fjKCOM0r_euWhIprM9crfQ",MAPS_API_KEY="AIzaSyBY4CCIFbyI3FH59aSkifR9-ThyY0Na8l0"