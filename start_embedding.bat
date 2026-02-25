@echo off
echo ============================================================
echo Starting Full Embedding Generation
echo ============================================================
echo.
echo This will process all 698 conversations (~1.66M messages)
echo Estimated time: 6-12 hours
echo.
echo Progress will be saved to: logs/embedding_generation.log
echo Checkpoint file: vector_stores/generation_checkpoint.pkl
echo.
echo Press Ctrl+C to stop (progress will be saved)
echo.
echo ============================================================
echo.

cd /d D:\导出聊天记录excel
call venv_embedding\Scripts\activate.bat
python -u generate_all_embeddings.py 2>&1 | tee logs\embedding_generation.log

pause
