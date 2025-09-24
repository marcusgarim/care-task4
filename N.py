import logging
from datetime import datetime, time, timedelta, date
from typing import List, Dict, Any, Optional, Union
from pytz import timezone
import traceback

from professionals_api.models.models import ProfessionalAvailability, AvailabilitySlot
from professionals_api.data.database import Database

class ProfessionalService:
    def __init__(self, db_or_connection_string):
        """
        Initialize ProfessionalService with either a Database object or a connection string
        
        Args:
            db_or_connection_string: Either a Database object or a connection string
        """
        if isinstance(db_or_connection_string, str):
            # It's a connection string
            self.db = Database(db_or_connection_string)
            self._owns_db = True
        else:
            # It's a Database object
            self.db = db_or_connection_string
            self._owns_db = False
    
    async def __aenter__(self):
        if self._owns_db:
            await self.db.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_db:
            await self.db.disconnect()
    
    async def set_availability(self, availability: ProfessionalAvailability) -> Dict[str, Any]:
        """
        Set the professional availability for the week
        
        Args:
            availability: The availability model with professional_id and weekly schedule
            
        Returns:
            Dictionary with success status and message or error
        """
        try:
            # Check if professional exists
            professional_id = availability.professional_id
            logging.info(f"Executing query with ID: {professional_id}, type: {type(professional_id)}")
            
            # If professional_id is an email, get the ID
            if '@' in professional_id:
                query = """
                SELECT id FROM disponibilidade_profissionais.profissionais 
                WHERE email = $1
                """
                result = await self.db.fetch_one(query, (professional_id,))
                if not result:
                    return {"success": False, "error": f"Professional with email {professional_id} not found"}
                professional_id = result['id']
            else:
                # Try to convert to integer
                try:
                    professional_id = int(professional_id)
                except ValueError:
                    return {"success": False, "error": f"Invalid professional ID format: {professional_id}"}
                    
                # Validate ID exists
                query = """
                SELECT id FROM disponibilidade_profissionais.profissionais 
                WHERE id = $1
                """
                result = await self.db.fetch_one(query, (professional_id,))
                if not result:
                    return {"success": False, "error": f"Professional with ID {professional_id} not found"}
                    
            logging.info(f"After processing, ID: {professional_id}, type: {type(professional_id)}")
            
            # Delete existing availability for this professional
            delete_query = """
            DELETE FROM disponibilidade_profissionais.disponibilidades
            WHERE profissional_id = $1
            """
            await self.db.execute(delete_query, (professional_id,))
            
            # Insert new availability
            for avail in availability.professional_schedule:
                if avail.type == "off":
                    # For off days, store with null hours
                    insert_query = """
                    INSERT INTO disponibilidade_profissionais.disponibilidades
                    (profissional_id, dia_semana, hora_inicio, hora_fim, tipo_atendimento)
                    VALUES ($1, $2, NULL, NULL, $3)
                    """
                    await self.db.execute(insert_query, (
                        professional_id,
                        avail.dayOfWeek,
                        self._map_type_to_db(avail.type)  # Map English type to Portuguese database value
                    ))
                else:
                    # Convert time strings to time objects
                    start_time = datetime.strptime(avail.start, "%H:%M").time() if avail.start else None
                    end_time = datetime.strptime(avail.end, "%H:%M").time() if avail.end else None
                    break_start_time = datetime.strptime(avail.breakStart, "%H:%M").time() if avail.breakStart else None
                    break_end_time = datetime.strptime(avail.breakEnd, "%H:%M").time() if avail.breakEnd else None
                    
                    # For working days, store with all details
                    insert_query = """
                    INSERT INTO disponibilidade_profissionais.disponibilidades
                    (profissional_id, dia_semana, hora_inicio, hora_fim, tipo_atendimento, intervalo_inicio, intervalo_fim)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """
                    await self.db.execute(insert_query, (
                        professional_id,
                        avail.dayOfWeek,
                        start_time,
                        end_time,
                        self._map_type_to_db(avail.type),
                        break_start_time,
                        break_end_time
                    ))
            
            return {"success": True, "message": "Availability has been updated successfully"}
            
        except Exception as e:
            logging.error(f"Error setting professional availability: {str(e)}")
            return {"success": False, "error": f"Failed to set availability: {str(e)}"}
    
    async def get_availability(self, professional_id: str) -> Dict[str, Any]:
        """
        Get the professional availability for the week
        
        Args:
            professional_id: The professional ID or email
            
        Returns:
            Dictionary with success status and availability data or error
        """
        try:
            # Ensure professional_id is a string for email checking
            professional_id_str = str(professional_id)
            
            # If professional_id is an email, get the ID
            if '@' in professional_id_str:
                query = """
                SELECT id FROM disponibilidade_profissionais.profissionais 
                WHERE email = $1
                """
                result = await self.db.fetch_one(query, (professional_id_str,))
                if not result:
                    return {"success": False, "error": f"Professional with email {professional_id_str} not found"}
                professional_id = result['id']
            else:
                # Try to convert to integer for database query
                try:
                    professional_id = int(professional_id_str)
                except ValueError:
                    return {"success": False, "error": f"Invalid professional ID format: {professional_id_str}"}
            
            # Get the availability
            query = """
            SELECT dia_semana, hora_inicio, hora_fim, tipo_atendimento, intervalo_inicio, intervalo_fim
            FROM disponibilidade_profissionais.disponibilidades
            WHERE profissional_id = $1
            ORDER BY dia_semana
            """
            results = await self.db.fetch_all(query, (professional_id,))
            
            if not results:
                return {"success": False, "error": f"No availability found for professional with ID {professional_id}"}
            
            # Format the results
            availability = []
            for row in results:
                avail_item = {
                    "dayOfWeek": row["dia_semana"],
                    "attendance_type": self._map_type_from_db(row["tipo_atendimento"])
                }
                
                if row["tipo_atendimento"] != "indisponivel":
                    avail_item.update({ 
                        "start": row["hora_inicio"].strftime("%H:%M") if row["hora_inicio"] else None,
                        "end": row["hora_fim"].strftime("%H:%M") if row["hora_fim"] else None,
                        "breakStart": row["intervalo_inicio"].strftime("%H:%M") if row["intervalo_inicio"] else None,
                        "breakEnd": row["intervalo_fim"].strftime("%H:%M") if row["intervalo_fim"] else None
                    })
                
                availability.append(avail_item)
            
            return {
                "success": True,
                "professional_id": professional_id,
                "professional_schedule": availability
            }
            
        except Exception as e:
            logging.error(f"Error getting professional availability: {str(e)}")
            return {"success": False, "error": f"Failed to get availability: {str(e)}"}
        
    
    async def get_professional_calendar_id(self, professional_id: str) -> Dict[str, Any]:
        """
        Get the professional's Google Calendar ID
        
        Args:
            professional_id: The professional ID or email
            
        Returns:
            Dictionary with success status and calendar ID or error
        """
        try:
            # Ensure professional_id is a string
            professional_id_str = str(professional_id)
            logging.info(f"get_professional_calendar_id: Input professional_id={professional_id}, type={type(professional_id)}, after str conversion={professional_id_str}")
            
            # If professional_id is an email, get the ID and use the email as calendar ID
            if '@' in professional_id_str:
                logging.info(f"get_professional_calendar_id: Treating as email: {professional_id_str}")
                query = """
                SELECT id FROM disponibilidade_profissionais.profissionais 
                WHERE email = $1
                """
                result = await self.db.fetch_one(query, (professional_id_str,))
                if not result:
                    logging.error(f"get_professional_calendar_id: No professional found with email {professional_id_str}")
                    return {"success": False, "error": f"Professional with email {professional_id_str} not found"}
                
                logging.info(f"get_professional_calendar_id: Found professional with ID {result['id']} for email {professional_id_str}")
                # Use the email as calendar ID
                return {
                    "success": True,
                    "calendar_id": professional_id_str  # Using the email as the calendar ID
                }
            else:
                # Convert to integer for database query if it's numeric
                try:
                    professional_id_int = int(professional_id_str)
                    logging.info(f"get_professional_calendar_id: Converted to integer: {professional_id_int}")
                    # Get the email using the ID
                    query = """
                    SELECT email FROM disponibilidade_profissionais.profissionais 
                    WHERE id = $1
                    """
                    result = await self.db.fetch_one(query, (professional_id_int,))
                    if not result or not result.get('email'):
                        logging.error(f"get_professional_calendar_id: No professional found with ID {professional_id_int}")
                        return {"success": False, "error": f"No valid email found for professional with ID {professional_id_str}"}
                    
                    logging.info(f"get_professional_calendar_id: Found professional with email {result['email']} for ID {professional_id_int}")
                    # Use the email as calendar ID
                    return {
                        "success": True,
                        "calendar_id": result['email']
                    }
                except ValueError as ve:
                    # Not a valid integer
                    logging.error(f"get_professional_calendar_id: Invalid ID format (not an integer): {professional_id_str} - {str(ve)}")
                    return {"success": False, "error": f"Invalid professional ID format: {professional_id_str}"}
            
        except Exception as e:
            logging.error(f"Error getting professional calendar ID: {str(e)}")
            return {"success": False, "error": f"Failed to get calendar ID: {str(e)}"}
        
    async def get_available_slots(
        self, 
        professional_id: str, 
        start_datetime: datetime, 
        end_datetime: datetime, 
        calendar_id: str,
        calendar_service,
        interval: int = 60,
        next_events: int = 3,
        attendance_type: int = 3  # Default to both (3)
    ) -> List[AvailabilitySlot]:
        """
        Get available slots for a professional based on their availability and calendar
        
        Args:
            professional_id: The professional ID or email
            start_datetime: The start datetime to check availability
            end_datetime: The end datetime to check availability
            calendar_id: The Google Calendar ID
            calendar_service: The CalendarAction service object
            interval: The duration of each slot in minutes
            next_events: The number of available slots to return
            attendance_type: The type of attendance (1=in person, 2=online, 3=both)
            
        Returns:
            List of available time slots
        """
        try:
            # Ensure professional_id is a string
            professional_id = str(professional_id)
            
            # Ensure timezone awareness
            sao_paulo_tz = timezone('America/Sao_Paulo')
            if start_datetime.tzinfo is None:
                start_datetime = sao_paulo_tz.localize(start_datetime)
            if end_datetime.tzinfo is None:
                end_datetime = sao_paulo_tz.localize(end_datetime)
            
            # Get professional availability
            availability_result = await self.get_availability(professional_id)
            if not availability_result["success"]:
                raise Exception(availability_result["error"])
            
            availability = availability_result["professional_schedule"]
            logging.info(f"Professional availability: {availability}")
            
            # Initialize variables
            available_slots = []
            current_date = start_datetime.date()
            max_days_to_check = 30  # Limit to avoid infinite loops
            
            # Check each day until we find enough slots or reach the max days
            while len(available_slots) < next_events and max_days_to_check > 0:
                # Get day of week (1-7, where 1 is Monday)
                day_of_week = current_date.weekday() + 1  # Keep as integer
                logging.info(f"Checking day {current_date} (day of week {day_of_week})")
                
                # Find availability for this day
                day_availability = next((a for a in availability if a["dayOfWeek"] == day_of_week), None)
                
                if not day_availability or day_availability["attendance_type"] == "off":
                    logging.info(f"Professional is not available on {current_date}")
                    current_date += timedelta(days=1)
                    max_days_to_check -= 1
                    continue
                
                # Check if the day's availability type matches the requested type
                day_type = day_availability["attendance_type"]
                logging.info(f"Checking day type {day_type} against attendance type {attendance_type}")
                
                # Map attendance types to allowed day types
                allowed_types = {
                    1: ["in_person", "office", "hybrid"],  # In-person
                    2: ["online", "home", "hybrid"],       # Online
                    3: ["in_person", "office", "online", "home", "hybrid"]  # Both
                }
                
                if day_type not in allowed_types.get(attendance_type, []):
                    logging.info(f"Skipping day {current_date} - type {day_type} not allowed for attendance type {attendance_type}")
                    current_date += timedelta(days=1)
                    max_days_to_check -= 1
                    continue
                
                # Get working hours for this day
                work_start = datetime.strptime(day_availability["start"], "%H:%M").time()
                work_end = datetime.strptime(day_availability["end"], "%H:%M").time()
                
                # Create datetime objects for the day
                day_start = datetime.combine(current_date, work_start)
                day_end = datetime.combine(current_date, work_end)
                
                # Localize the datetimes
                day_start = sao_paulo_tz.localize(day_start)
                day_end = sao_paulo_tz.localize(day_end)
                
                # Adjust start time if it's the first day
                if current_date == start_datetime.date():
                    day_start = max(day_start, start_datetime)
                
                # Check calendar availability for this day
                calendar_result = calendar_service.check_availability(
                    start_datetime=day_start.strftime("%Y-%m-%d %H:%M"),
                    end_datetime=day_end.strftime("%Y-%m-%d %H:%M"),
                    interval=interval,
                    start_time=day_start.strftime("%H:%M"),
                    end_time=day_end.strftime("%H:%M"),
                    calendar_id=calendar_id,
                    next_events=1000,  # Get all events in the period
                    break_start=day_availability.get("breakStart"),
                    break_end=day_availability.get("breakEnd")
                )
                
                if not calendar_result.get("success"):
                    logging.error(f"Failed to check calendar for {current_date}: {calendar_result.get('error')}")
                    current_date += timedelta(days=1)
                    max_days_to_check -= 1
                    continue
                
                # Process available slots from calendar
                for slot in calendar_result.get("available_slots", []):
                    try:
                        slot_start = datetime.strptime(slot["start"], "%Y-%m-%d %H:%M")
                        slot_end = datetime.strptime(slot["end"], "%Y-%m-%d %H:%M")
                        
                        # Localize the datetimes
                        slot_start = sao_paulo_tz.localize(slot_start)
                        slot_end = sao_paulo_tz.localize(slot_end)
                        
                        # Add the slot with service type
                        available_slots.append(AvailabilitySlot(
                            start=slot_start.strftime("%Y-%m-%d %H:%M"),
                            end=slot_end.strftime("%Y-%m-%d %H:%M"),
                            attendance_type=day_type
                        ))
                        logging.info(f"Added available slot: {slot_start} - {slot_end} (type: {day_type})")
                        
                        if len(available_slots) >= next_events:
                            logging.info(f"Found requested {next_events} available slots")
                            break
                            
                    except Exception as parse_error:
                        logging.error(f"Error parsing slot datetime: {str(parse_error)}, slot: {slot}")
                
                # Move to next day
                current_date += timedelta(days=1)
                max_days_to_check -= 1
            
            logging.info(f"Final available_slots length: {len(available_slots)}")
            for i, slot in enumerate(available_slots, 1):
                logging.info(f"Slot {i}: {slot.start} - {slot.end} (type: {slot.attendance_type})")
                
            return available_slots
            
        except Exception as e:
            logging.error(f"Error getting available slots: {str(e)}")
            raise
   
    async def create_professional(self, name: str, specialty: str, email: str, phone: str) -> Dict[str, Any]:
        """
        Create a new professional
        """
        try:
            # Validate email is unique
            query = """
            SELECT id FROM disponibilidade_profissionais.profissionais 
            WHERE email = $1
            """
            result = await self.db.fetch_one(query, (email,))
            if result:
                return {"success": False, "error": f"A professional with email {email} already exists"}
            
            # Insert new professional
            insert_query = """
            INSERT INTO disponibilidade_profissionais.profissionais
            (nome, especialidade, email, telefone)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """
            result = await self.db.fetch_one(insert_query, (name, specialty, email, phone))
            
            if not result:
                return {"success": False, "error": "Failed to create professional record"}
            
            return {
                "success": True, 
                "message": "Professional created successfully",
                "professional_id": result["id"]
            }
            
        except Exception as e:
            logging.error(f"Error creating professional: {str(e)}")
            return {"success": False, "error": f"Failed to create professional: {str(e)}"}

    def _map_type_to_db(self, type_value: str) -> str:
        """Maps English type values to Portuguese database values"""
        mapping = {
            "hybrid": "hibrido",
            "home": "remoto",
            "office": "presencial",
            "off": "indisponivel"
        }
        return mapping.get(type_value, type_value)
        
    def _map_type_from_db(self, db_value: str) -> str:
        """Maps Portuguese database values to English type values"""
        mapping = {
            "hibrido": "hybrid",
            "remoto": "home",
            "presencial": "office",
            "indisponivel": "off"
        }
        return mapping.get(db_value, db_value)

    async def get_or_create_client(self, email: str, name: str = None, celular: str = None, data_nascimento: str = None) -> Dict[str, Any]:
        """
        Get a client by email or create a new one if it doesn't exist
        
        Args:
            email: Client's email address
            name: Client's name (required for creation)
            celular: Client's phone number
            data_nascimento: Client's birth date
            
        Returns:
            Dictionary with client data and success status
        """
        try:
            # Check if client exists
            query = """
            SELECT id, nome, celular, data_nascimento, email
            FROM disponibilidade_profissionais.clientes
            WHERE email = $1
            """
            result = await self.db.fetch_one(query, (email,))
            
            if result:
                return {"success": True, "message": "Client found", "client": result}
            
            # Create new client if not exists
            if not name:
                return {"success": False, "error": "Name is required to create a new client"}
            
            # Convert date string to date object if provided
            birth_date = None
            if data_nascimento:
                try:
                    birth_date = datetime.strptime(data_nascimento, "%Y-%m-%d").date()
                except ValueError:
                    return {"success": False, "error": "Birth date must be in format YYYY-MM-DD"}
            
            # Insert new client
            insert_query = """
            INSERT INTO disponibilidade_profissionais.clientes
            (nome, celular, data_nascimento, email)
            VALUES ($1, $2, $3, $4)
            RETURNING id, nome, celular, data_nascimento, email
            """
            client = await self.db.fetch_one(insert_query, (name, celular, birth_date, email))
            
            if not client:
                return {"success": False, "error": "Failed to create client"}
            
            return {"success": True, "message": "Client created successfully", "client": client}
            
        except Exception as e:
            logging.error(f"Error in get_or_create_client: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    async def create_appointment(self, 
                                client_id: int = None, 
                                client_email: str = None,
                                professional_id: int = None,
                                professional_email: str = None,
                                data_consulta: str = None,
                                hora_inicio: str = None,
                                hora_fim: str = None,
                                observacao: str = None,
                                tipo_atendimento: str = None,
                                calendar_event_id: str = None) -> Dict[str, Any]:
        """
        Create a new appointment and link client with professional
        
        Args:
            client_id: ID of the client
            client_email: Email of the client (alternative to client_id)
            professional_id: ID of the professional
            professional_email: Email of the professional (alternative to professional_id)
            data_consulta: Date of the appointment
            hora_inicio: Start time of the appointment
            hora_fim: End time of the appointment
            observacao: Notes about the appointment
            tipo_atendimento: Type of appointment (hibrido, remoto, presencial)
            calendar_event_id: Google Calendar event ID if already created
            
        Returns:
            Dictionary with success status and appointment info
        """
        try:
            # Validate required parameters
            if not client_id and not client_email:
                return {"success": False, "error": "Either client_id or client_email must be provided"}
                
            if not professional_id and not professional_email:
                return {"success": False, "error": "Either professional_id or professional_email must be provided"}
                
            if not data_consulta or not hora_inicio or not hora_fim or not tipo_atendimento:
                return {"success": False, "error": "Appointment date, time and type are required"}
            
            # Get client ID if email is provided
            if not client_id and client_email:
                client_query = """
                SELECT id FROM disponibilidade_profissionais.clientes
                WHERE email = $1
                """
                client_result = await self.db.fetch_one(client_query, (client_email,))
                if not client_result:
                    return {"success": False, "error": f"Client with email {client_email} not found"}
                client_id = client_result['id']
            
            # Get professional ID if email is provided
            if not professional_id and professional_email:
                prof_query = """
                SELECT id FROM disponibilidade_profissionais.profissionais
                WHERE email = $1
                """
                prof_result = await self.db.fetch_one(prof_query, (professional_email,))
                if not prof_result:
                    return {"success": False, "error": f"Professional with email {professional_email} not found"}
                professional_id = prof_result['id']
            
            # Make sure professional_id is an integer
            if isinstance(professional_id, str):
                try:
                    if '@' in professional_id:
                        # This is an email address, look up the ID
                        prof_query = """
                        SELECT id FROM disponibilidade_profissionais.profissionais
                        WHERE email = $1
                        """
                        prof_result = await self.db.fetch_one(prof_query, (professional_id,))
                        if not prof_result:
                            return {"success": False, "error": f"Professional with email {professional_id} not found"}
                        professional_id = prof_result['id']
                    else:
                        # Try to convert to integer
                        professional_id = int(professional_id)
                except (ValueError, TypeError) as e:
                    return {"success": False, "error": f"Invalid professional ID format: {str(e)}"}
            
            # Parse date and time
            try:
                appointment_date = datetime.strptime(data_consulta, "%Y-%m-%d").date()
                start_time = datetime.strptime(hora_inicio, "%H:%M").time()
                end_time = datetime.strptime(hora_fim, "%H:%M").time()
            except ValueError as e:
                return {"success": False, "error": f"Date/time format error: {str(e)}"}
            
            # Create the appointment
            insert_query = """
            INSERT INTO disponibilidade_profissionais.agendamentos
            (cliente_id, profissional_id, data_consulta, hora_inicio, hora_fim, 
            observacao, tipo_atendimento, status, event_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """
            
            # Add event_id column if it doesn't exist
            try:
                # Check if column exists
                check_column_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema='disponibilidade_profissionais' 
                AND table_name='agendamentos' 
                AND column_name='event_id'
                """
                column_exists = await self.db.fetch_one(check_column_query)
                
                if not column_exists:
                    # Add event_id column
                    add_column_query = """
                    ALTER TABLE disponibilidade_profissionais.agendamentos
                    ADD COLUMN event_id VARCHAR(255)
                    """
                    await self.db.execute(add_column_query)
                    logging.info("Added event_id column to agendamentos table")
            except Exception as e:
                logging.warning(f"Error checking/adding event_id column: {str(e)}")
            
            # Insert appointment
            result = await self.db.fetch_one(insert_query, (
                client_id, 
                professional_id, 
                appointment_date, 
                start_time, 
                end_time, 
                observacao, 
                tipo_atendimento,
                0,  # Status: pending
                calendar_event_id
            ))
            
            if not result:
                return {"success": False, "error": "Failed to create appointment"}
            
            appointment_id = result['id']
            
            # Always create a relation between client and professional for appointments
            try:
                # Check if relation already exists
                relation_query = """
                SELECT id FROM disponibilidade_profissionais.profissional_cliente
                WHERE profissional_id = $1 AND cliente_id = $2
                """
                relation = await self.db.fetch_one(relation_query, (professional_id, client_id))
                
                if not relation:
                    # Create new relation
                    insert_relation_query = """
                    INSERT INTO disponibilidade_profissionais.profissional_cliente
                    (profissional_id, cliente_id, ativo)
                    VALUES ($1, $2, true)
                    """
                    await self.db.execute(insert_relation_query, (professional_id, client_id))
                    logging.info(f"Created relation between professional {professional_id} and client {client_id}")
            except Exception as e:
                logging.warning(f"Error creating professional-client relation: {str(e)}")
            
            return {
                "success": True, 
                "message": "Appointment created successfully",
                "appointment_id": appointment_id
            }
            
        except Exception as e:
            logging.error(f"Error in create_appointment: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    async def update_appointment_status(self, appointment_id: int, status: int) -> Dict[str, Any]:
        """
        Update the status of an appointment
        
        Args:
            appointment_id: ID of the appointment
            status: New status (0: pending, 1: confirmed, 2: cancelled)
            
        Returns:
            Dictionary with success status
        """
        try:
            if status not in [0, 1, 2]:
                return {"success": False, "error": "Invalid status value"}
                
            # Get current time for confirmation timestamp
            current_time = datetime.now()
            
            # Update appointment status
            update_query = """
            UPDATE disponibilidade_profissionais.agendamentos
            SET status = $1, data_confirmacao = $2
            WHERE id = $3
            RETURNING id
            """
            result = await self.db.fetch_one(update_query, (
                status,
                current_time if status == 1 else None,  # Only set confirmation date if status is confirmed
                appointment_id
            ))
            
            if not result:
                return {"success": False, "error": f"Appointment with ID {appointment_id} not found"}
                
            return {
                "success": True,
                "message": f"Appointment status updated to {status}"
            }
            
        except Exception as e:
            logging.error(f"Error in update_appointment_status: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    async def get_pending_confirmations(self, days_before: int = 2) -> Dict[str, Any]:
        """
        Get appointments that are pending confirmation and are scheduled in the next few days
        
        Args:
            days_before: Number of days before the appointment to check for confirmation
            
        Returns:
            Dictionary with success status and list of appointments
        """
        try:
            # Calculate target date
            target_date = datetime.now().date() + timedelta(days=days_before)
            
            # Get pending appointments
            query = """
            SELECT a.id, a.data_consulta, a.hora_inicio, a.hora_fim, a.tipo_atendimento,
                   c.id as client_id, c.nome as client_name, c.email as client_email,
                   p.id as professional_id, p.nome as professional_name, p.email as professional_email,
                   a.event_id
            FROM disponibilidade_profissionais.agendamentos a
            JOIN disponibilidade_profissionais.clientes c ON a.cliente_id = c.id
            JOIN disponibilidade_profissionais.profissionais p ON a.profissional_id = p.id
            WHERE a.status = 0 AND a.data_consulta = $1
            """
            results = await self.db.fetch_all(query, (target_date,))
            
            appointments = []
            for row in results:
                appointment = dict(row)
                # Format dates for better readability
                if isinstance(appointment.get('data_consulta'), date):
                    appointment['data_consulta'] = appointment['data_consulta'].strftime("%Y-%m-%d")
                if isinstance(appointment.get('hora_inicio'), time):
                    appointment['hora_inicio'] = appointment['hora_inicio'].strftime("%H:%M")
                if isinstance(appointment.get('hora_fim'), time):
                    appointment['hora_fim'] = appointment['hora_fim'].strftime("%H:%M")
                appointments.append(appointment)
            
            return {
                "success": True,
                "appointments": appointments,
                "total": len(appointments)
            }
            
        except Exception as e:
            logging.error(f"Error in get_pending_confirmations: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    async def create_appointment_with_calendar_event(self, appointment_data: dict, calendar_service) -> Dict[str, Any]:
        """
        Create an appointment and a calendar event
        
        Args:
            appointment_data: Appointment data dictionary
            calendar_service: Google Calendar service instance
            
        Returns:
            Dictionary with success status and appointment info
        """
        try:
            # Get client information
            client_id = appointment_data.get('client_id')
            client_email = appointment_data.get('client_email')
            client_name = appointment_data.get('client_name')
            client = None
            
            # Process professional ID
            professional_id = appointment_data.get('professional_id')
            professional_email = None
            
            # If professional_id is an email address, use it as professional_email
            if isinstance(professional_id, str) and '@' in professional_id:
                professional_email = professional_id
                professional_id = None
                
                # Look up the professional ID from email
                prof_query = """
                SELECT id FROM disponibilidade_profissionais.profissionais
                WHERE email = $1
                """
                prof_result = await self.db.fetch_one(prof_query, (professional_email,))
                if prof_result:
                    professional_id = prof_result['id']
                else:
                    return {"success": False, "error": f"Professional with email {professional_email} not found"}
                    
            # Check if client already exists
            if client_id:
                # Fetch client by ID
                client_query = """
                SELECT id, email, nome FROM disponibilidade_profissionais.clientes
                WHERE id = $1
                """
                client = await self.db.fetch_one(client_query, (client_id,))
            elif client_email:
                # Fetch client by email
                client_query = """
                SELECT id, email, nome FROM disponibilidade_profissionais.clientes
                WHERE email = $1
                """
                client = await self.db.fetch_one(client_query, (client_email,))
            
            # If client doesn't exist, create a new one
            if not client:
                if not client_email or not client_name:
                    return {"success": False, "error": "Client email and name are required for new clients"}
                
                client_result = await self.get_or_create_client(
                    email=client_email,
                    name=client_name,
                    celular=appointment_data.get('client_phone'),
                    data_nascimento=appointment_data.get('client_birth_date')
                )
                
                if not client_result['success']:
                    return {"success": False, "error": f"Failed to create client: {client_result.get('error')}"}
                
                client = {
                    'id': client_result['client']['id'],
                    'email': client_email,
                    'nome': client_name
                }
            
            # Get professional calendar ID
            calendar_id_result = await self.get_professional_calendar_id(
                professional_id if not professional_email else professional_email
            )
            
            if not calendar_id_result['success']:
                return {"success": False, "error": f"Failed to get professional's calendar: {calendar_id_result.get('error')}"}
            
            calendar_id = calendar_id_result['calendar_id']
            
            # Format date and time for Google Calendar
            appointment_date = appointment_data['data_consulta']
            start_time = appointment_data['hora_inicio']
            end_time = appointment_data['hora_fim']
            
            start_datetime = f"{appointment_date} {start_time}"
            end_datetime = f"{appointment_date} {end_time}"
            
            # Prepare calendar event participants
            participants = [client['email']]
            
            # Try to create calendar event
            calendar_event = calendar_service.create_event(
                titulo=appointment_data.get('titulo', f"Consulta com {client['nome']}"),
                descricao=appointment_data.get('descricao', ''),
                inicio=start_datetime,
                fim=end_datetime,
                participantes=participants,
                calendar_id=calendar_id
            )
            
            if not calendar_event['success']:
                return {"success": False, "error": f"Failed to create calendar event: {calendar_event.get('error')}"}
            
            # Create appointment in database
            appointment_result = await self.create_appointment(
                client_id=client['id'],
                professional_id=professional_id,
                professional_email=professional_email,
                data_consulta=appointment_date,
                hora_inicio=start_time,
                hora_fim=end_time,
                observacao=appointment_data.get('observacao'),
                tipo_atendimento=appointment_data['tipo_atendimento'],
                calendar_event_id=calendar_event['event_id']
            )
            
            if not appointment_result['success']:
                # Try to delete the calendar event if appointment creation fails
                try:
                    calendar_service.delete_event(
                        event_id=calendar_event['event_id'],
                        calendar_id=calendar_id
                    )
                except Exception as e:
                    logging.error(f"Failed to delete calendar event after appointment creation failure: {str(e)}")
                
                return appointment_result
            
            # Return combined result
            return {
                "success": True,
                "message": "Appointment and calendar event created successfully",
                "appointment_id": appointment_result['appointment_id'],
                "calendar_event": {
                    "event_id": calendar_event['event_id'],
                    "html_link": calendar_event.get('html_link'),
                    "meet_link": calendar_event.get('meet_link')
                }
            }
            
        except Exception as e:
            logging.error(f"Error in create_appointment_with_calendar_event: {str(e)}")
            logging.error(traceback.format_exc())
            return {"success": False, "error": f"Error creating appointment: {str(e)}"}
    
    async def get_client_appointments(self, 
                                    client_id: int = None, 
                                    client_email: str = None, 
                                    professional_id: int = None,
                                    include_past: bool = False) -> Dict[str, Any]:
        """
        Get appointments for a client, optionally filtered by professional
        
        Args:
            client_id: ID of the client
            client_email: Email of the client (alternative to client_id)
            professional_id: ID of the professional (optional filter)
            include_past: Whether to include past appointments
            
        Returns:
            Dictionary with success status and list of appointments
        """
        try:
            # Validate parameters
            if not client_id and not client_email:
                return {"success": False, "error": "Either client_id or client_email must be provided"}
            
            # Get client ID if email is provided
            if not client_id and client_email:
                client_query = """
                SELECT id FROM disponibilidade_profissionais.clientes
                WHERE email = $1
                """
                client_result = await self.db.fetch_one(client_query, (client_email,))
                if not client_result:
                    return {"success": False, "error": f"Client with email {client_email} not found"}
                client_id = client_result['id']
            
            # Build query based on filters
            query = """
            SELECT a.id, a.data_consulta, a.hora_inicio, a.hora_fim, a.tipo_atendimento, a.status,
                  a.observacao, a.data_agendamento, a.data_confirmacao, a.event_id,
                  p.id as professional_id, p.nome as professional_name, p.email as professional_email,
                  p.especialidade as professional_specialty
            FROM disponibilidade_profissionais.agendamentos a
            JOIN disponibilidade_profissionais.profissionais p ON a.profissional_id = p.id
            WHERE a.cliente_id = $1
            """
            
            params = [client_id]
            param_index = 2
            
            if professional_id:
                query += f" AND a.profissional_id = ${param_index}"
                params.append(professional_id)
                param_index += 1
            
            if not include_past:
                query += f" AND (a.data_consulta > CURRENT_DATE OR (a.data_consulta = CURRENT_DATE AND a.hora_fim >= CURRENT_TIME))"
            
            query += " ORDER BY a.data_consulta ASC, a.hora_inicio ASC"
            
            results = await self.db.fetch_all(query, tuple(params))
            
            appointments = []
            for row in results:
                appointment = dict(row)
                # Format dates for better readability
                if isinstance(appointment.get('data_consulta'), date):
                    appointment['data_consulta'] = appointment['data_consulta'].strftime("%Y-%m-%d")
                if isinstance(appointment.get('hora_inicio'), time):
                    appointment['hora_inicio'] = appointment['hora_inicio'].strftime("%H:%M")
                if isinstance(appointment.get('hora_fim'), time):
                    appointment['hora_fim'] = appointment['hora_fim'].strftime("%H:%M")
                if isinstance(appointment.get('data_agendamento'), datetime):
                    appointment['data_agendamento'] = appointment['data_agendamento'].isoformat()
                if isinstance(appointment.get('data_confirmacao'), datetime):
                    appointment['data_confirmacao'] = appointment['data_confirmacao'].isoformat()
                    
                appointments.append(appointment)
            
            return {
                "success": True,
                "appointments": appointments,
                "total": len(appointments)
            }
            
        except Exception as e:
            logging.error(f"Error in get_client_appointments: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}

    async def manage_client_sharing(self, 
                                 client_id: Optional[int] = None,
                                 client_email: Optional[str] = None,
                                 permissions: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Manage sharing permissions for a client
        
        Args:
            client_id: ID of the client
            client_email: Email of the client (alternative to client_id)
            permissions: List of permission items with professional_id and can_access
            
        Returns:
            Dictionary with success status
        """
        try:
            if not client_id and not client_email:
                return {"success": False, "error": "Either client_id or client_email must be provided"}
            
            if not permissions or not isinstance(permissions, list):
                return {"success": False, "error": "Permissions list is required"}
            
            # Get client ID if email is provided
            if not client_id and client_email:
                client_query = """
                SELECT id FROM disponibilidade_profissionais.clientes
                WHERE email = $1
                """
                client_result = await self.db.fetch_one(client_query, (client_email,))
                if not client_result:
                    return {"success": False, "error": f"Client with email {client_email} not found"}
                client_id = client_result['id']
            
            results = {
                "success": True,
                "updated": 0,
                "errors": []
            }
            
            # Process each permission
            for permission in permissions:
                try:
                    professional_id = permission.get('professional_id')
                    can_access = permission.get('can_access', False)
                    
                    # Handle if professional_id is an email
                    if isinstance(professional_id, str) and '@' in professional_id:
                        prof_query = """
                        SELECT id FROM disponibilidade_profissionais.profissionais
                        WHERE email = $1
                        """
                        prof_result = await self.db.fetch_one(prof_query, (professional_id,))
                        if not prof_result:
                            results["errors"].append(f"Professional with email {professional_id} not found")
                            continue
                        professional_id = prof_result['id']
                    else:
                        # Convert to integer if needed
                        try:
                            professional_id = int(professional_id)
                            # Verify this professional exists
                            verify_query = """
                            SELECT id FROM disponibilidade_profissionais.profissionais
                            WHERE id = $1
                            """
                            verify_result = await self.db.fetch_one(verify_query, (professional_id,))
                            if not verify_result:
                                results["errors"].append(f"Professional with ID {professional_id} not found")
                                continue
                        except (ValueError, TypeError):
                            results["errors"].append(f"Invalid professional ID format: {professional_id}")
                            continue
                    
                    # Check if relation already exists
                    relation_query = """
                    SELECT id, ativo FROM disponibilidade_profissionais.profissional_cliente
                    WHERE profissional_id = $1 AND cliente_id = $2
                    """
                    relation = await self.db.fetch_one(relation_query, (professional_id, client_id))
                    
                    if can_access:
                        # Grant access
                        if not relation:
                            # Create new relation
                            insert_query = """
                            INSERT INTO disponibilidade_profissionais.profissional_cliente
                            (profissional_id, cliente_id, ativo)
                            VALUES ($1, $2, true)
                            """
                            await self.db.execute(insert_query, (professional_id, client_id))
                        elif not relation.get('ativo'):
                            # Reactivate existing relation
                            update_query = """
                            UPDATE disponibilidade_profissionais.profissional_cliente
                            SET ativo = true
                            WHERE profissional_id = $1 AND cliente_id = $2
                            """
                            await self.db.execute(update_query, (professional_id, client_id))
                    else:
                        # Revoke access
                        if relation:
                            # Deactivate relation
                            update_query = """
                            UPDATE disponibilidade_profissionais.profissional_cliente
                            SET ativo = false
                            WHERE profissional_id = $1 AND cliente_id = $2
                            """
                            await self.db.execute(update_query, (professional_id, client_id))
                    
                    results["updated"] += 1
                    
                except Exception as e:
                    logging.error(f"Error processing permission for professional {permission.get('professional_id')}: {str(e)}")
                    results["errors"].append(f"Error for professional {permission.get('professional_id')}: {str(e)}")
            
            if results["updated"] == 0 and len(results["errors"]) > 0:
                return {"success": False, "errors": results["errors"]}
            
            return results
            
        except Exception as e:
            logging.error(f"Error in manage_client_sharing: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
            
    async def get_professional_clients(self, professional_id: Union[int, str], include_inactive: bool = False) -> Dict[str, Any]:
        """
        Get clients associated with a professional
        
        Args:
            professional_id: ID or email of the professional
            include_inactive: Whether to include inactive relationships
            
        Returns:
            Dictionary with success status and list of clients
        """
        try:
            # If professional_id is an email, get the actual ID
            if isinstance(professional_id, str) and '@' in professional_id:
                prof_query = """
                SELECT id FROM disponibilidade_profissionais.profissionais
                WHERE email = $1
                """
                prof_result = await self.db.fetch_one(prof_query, (professional_id,))
                if not prof_result:
                    return {"success": False, "error": f"Professional with email {professional_id} not found"}
                professional_id = prof_result['id']
            else:
                # Ensure professional_id is an integer
                try:
                    professional_id = int(professional_id)
                except (ValueError, TypeError):
                    return {"success": False, "error": f"Invalid professional ID format: {professional_id}"}
                
                # Verify this professional exists
                verify_query = """
                SELECT id FROM disponibilidade_profissionais.profissionais
                WHERE id = $1
                """
                verify_result = await self.db.fetch_one(verify_query, (professional_id,))
                if not verify_result:
                    return {"success": False, "error": f"Professional with ID {professional_id} not found"}
            
            # Build query to get clients
            query = """
            SELECT c.id, c.nome, c.email, c.celular, c.data_nascimento, pc.ativo
            FROM disponibilidade_profissionais.clientes c
            JOIN disponibilidade_profissionais.profissional_cliente pc ON c.id = pc.cliente_id
            WHERE pc.profissional_id = $1
            """
            
            if not include_inactive:
                query += " AND pc.ativo = true"
                
            query += " ORDER BY c.nome ASC"
            
            clients = await self.db.fetch_all(query, (professional_id,))
            
            # Format date fields
            formatted_clients = []
            for client in clients:
                client_dict = dict(client)
                # Format date_nascimento if available
                if client_dict.get('data_nascimento'):
                    client_dict['data_nascimento'] = client_dict['data_nascimento'].strftime('%Y-%m-%d')
                formatted_clients.append(client_dict)
            
            return {
                "success": True,
                "clients": formatted_clients,
                "total": len(formatted_clients)
            }
            
        except Exception as e:
            logging.error(f"Error in get_professional_clients: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}