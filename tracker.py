"""
Modul tracking resi menggunakan BinderByte API.
Daftar gratis di: https://binderbyte.com
Mendukung 60+ kurir Indonesia dan internasional.
"""

import aiohttp
import logging

logger = logging.getLogger(__name__)

BINDERBYTE_BASE_URL = "https://api.binderbyte.com/v1/track"


class Tracker:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def check(self, resi: str, courier: str) -> dict:
        """
        Cek status resi melalui BinderByte API.
        
        Returns:
            dict dengan keys: success, last_status, history, error
        """
        try:
            params = {
                "api_key": self.api_key,
                "courier": courier.lower(),
                "awb": resi
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    BINDERBYTE_BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    data = await response.json()

            logger.info(f"API Response untuk {resi}: status={data.get('status')}")

            # Cek respons API
            if data.get("status") == 200 and data.get("data"):
                raw = data["data"]
                summary = raw.get("summary", {})
                history = raw.get("history", [])

                # Ambil status terakhir
                last_status = (
                    summary.get("status") or
                    (history[0].get("desc") if history else "Status tidak tersedia")
                )

                # Format history
                formatted_history = []
                for item in history:
                    formatted_history.append({
                        "date": item.get("date", ""),
                        "desc": item.get("desc", ""),
                        "location": item.get("location", "")
                    })

                return {
                    "success": True,
                    "last_status": last_status,
                    "history": formatted_history,
                    "raw": raw
                }

            else:
                error_msg = data.get("message", "Resi tidak ditemukan atau kurir salah")
                logger.warning(f"API error untuk {resi}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "last_status": "",
                    "history": []
                }

        except aiohttp.ClientTimeout:
            return {
                "success": False,
                "error": "Timeout - Server tidak merespons",
                "last_status": "",
                "history": []
            }
        except aiohttp.ClientError as e:
            logger.error(f"Network error untuk {resi}: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "last_status": "",
                "history": []
            }
        except Exception as e:
            logger.error(f"Unexpected error untuk {resi}: {e}")
            return {
                "success": False,
                "error": f"Error tidak terduga: {str(e)}",
                "last_status": "",
                "history": []
            }

    @staticmethod
    def detect_courier(resi: str) -> str | None:
        """
        Deteksi kurir berdasarkan format nomor resi.
        Ini hanya perkiraan - tidak 100% akurat.
        """
        resi = resi.strip().upper()

        patterns = {
            "jne": lambda r: (r.startswith("JD") and len(r) == 12) or
                             (r.startswith("JE") and len(r) == 12),
            "jnt": lambda r: r.startswith("JP") or (r.isdigit() and len(r) == 12),
            "sicepat": lambda r: r.startswith("01") or r.startswith("00") and len(r) == 18,
            "anteraja": lambda r: r.startswith("GA") or r.startswith("MH"),
            "pos": lambda r: r.isdigit() and len(r) == 13 and r.endswith("ID"),
            "lion": lambda r: r.startswith("LB") or r.startswith("CJ"),
            "tiki": lambda r: len(r) == 10 and r.isdigit(),
        }

        for courier, check in patterns.items():
            try:
                if check(resi):
                    return courier
            except Exception:
                pass

        return None
